/*
 * sebatt_fw.c — MicroBlaze firmware for SeBatt PoC
 * Hackathon Deeptech 2026
 *
 * Auth flow:
 *   1. Wait for AUTH_REQ packet from station via UART
 *   2. Extract nonce (32 bytes)
 *   3. Build message: nonce || battery_id || voltage
 *   4. Write key + message to HMAC IP, start computation
 *   5. Read HMAC result
 *   6. Send AUTH_RESP packet back via UART
 *
 * Wire protocol (matches model/protocol.py):
 *   Frame: [CMD:1][LEN:2 big-endian][PAYLOAD:LEN][CRC8:1]
 *   AUTH_REQ  (0x01): payload = nonce (32 bytes)
 *   AUTH_RESP (0x02): payload = battery_id(4) + voltage(2) + hmac(32) = 38 bytes
 *   RESULT    (0x03): payload = status (1 byte)
 *   LOCK      (0x04): payload = none
 *   UNLOCK    (0x05): payload = none
 *   STATUS    (0x06): payload = none
 *
 * Build with Vitis:
 *   Create Application Project → Empty C → add this file
 *   BSP: standalone, with xil_printf
 */

#include "xil_io.h"
#include "xil_printf.h"
#include "xuartlite.h"
#include "xparameters.h"

#include <string.h>

/* ------------------------------------------------------------------ */
/* Hardware addresses (must match create_bd.tcl address map)           */
/* ------------------------------------------------------------------ */
#define HMAC_BASEADDR   0x44A00000

/* HMAC register offsets */
#define HMAC_CTRL       0x00
#define HMAC_STATUS     0x04
#define HMAC_MSG_LEN    0x08
#define HMAC_KEY_BASE   0x10   /* 0x10–0x2C: 8 words */
#define HMAC_MSG_BASE   0x30   /* 0x30–0x6C: 16 words */
#define HMAC_HASH_BASE  0x70   /* 0x70–0x8C: 8 words */

/* HMAC control bits */
#define HMAC_CTRL_START 0x01
#define HMAC_CTRL_INIT  0x02

/* HMAC status bits */
#define HMAC_STATUS_DONE 0x01
#define HMAC_STATUS_BUSY 0x02

/* Protocol commands */
#define CMD_AUTH_REQ    0x01
#define CMD_AUTH_RESP   0x02
#define CMD_RESULT      0x03
#define CMD_LOCK        0x04
#define CMD_UNLOCK      0x05
#define CMD_STATUS      0x06

/* SeBatt constants */
#define NONCE_LEN       32
#define BATTERY_ID_LEN  4
#define VOLTAGE_LEN     2
#define HMAC_LEN        32
#define MSG_LEN         (NONCE_LEN + BATTERY_ID_LEN + VOLTAGE_LEN)  /* 38 */
#define AUTH_RESP_LEN   (BATTERY_ID_LEN + VOLTAGE_LEN + HMAC_LEN)   /* 38 */

/* Max frame: CMD(1) + LEN(2) + PAYLOAD(38) + CRC(1) = 42 */
#define MAX_FRAME_LEN   64

/* ------------------------------------------------------------------ */
/* Battery identity (fixed for PoC)                                    */
/* ------------------------------------------------------------------ */
static const u8 battery_id[BATTERY_ID_LEN] = {0x42, 0x41, 0x54, 0x01}; /* "BAT\x01" */
static u16 voltage_mv = 3700;  /* Simulated ADC reading */
static u8  locked = 0;

/* Fixed key — matches Python model default: bytes(range(32)) */
static const u32 default_key[8] = {
    0x00010203, 0x04050607, 0x08090A0B, 0x0C0D0E0F,
    0x10111213, 0x14151617, 0x18191A1B, 0x1C1D1E1F
};

/* ------------------------------------------------------------------ */
/* UART helpers                                                        */
/* ------------------------------------------------------------------ */
static XUartLite uart;

static void uart_init(void) {
#ifdef SDT
    /* System Device Tree BSPs identify UARTLite instances by base address. */
    XUartLite_Initialize(&uart, XPAR_AXI_UARTLITE_0_BASEADDR);
#else
    XUartLite_Initialize(&uart, XPAR_AXI_UARTLITE_0_DEVICE_ID);
#endif
}

static u8 uart_recv_byte(void) {
    u8 c;
    while (XUartLite_Recv(&uart, &c, 1) == 0)
        ;
    return c;
}

static void uart_send_byte(u8 c) {
    while (XUartLite_Send(&uart, &c, 1) == 0)
        ;
}

static void uart_send_buf(const u8 *buf, int len) {
    for (int i = 0; i < len; i++)
        uart_send_byte(buf[i]);
}

/* ------------------------------------------------------------------ */
/* CRC-8/MAXIM (matches model/protocol.py)                             */
/* ------------------------------------------------------------------ */
static u8 crc8(const u8 *data, int len) {
    u8 crc = 0x00;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x31;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/* ------------------------------------------------------------------ */
/* Frame decode/encode                                                 */
/* ------------------------------------------------------------------ */
static int recv_frame(u8 *cmd, u8 *payload, u16 *payload_len) {
    /* Read header: CMD(1) + LEN(2) */
    *cmd = uart_recv_byte();
    u8 len_hi = uart_recv_byte();
    u8 len_lo = uart_recv_byte();
    *payload_len = ((u16)len_hi << 8) | len_lo;

    if (*payload_len > MAX_FRAME_LEN)
        return -1;

    /* Read payload */
    for (u16 i = 0; i < *payload_len; i++)
        payload[i] = uart_recv_byte();

    /* Read and verify CRC */
    u8 rx_crc = uart_recv_byte();
    u8 header[3] = {*cmd, len_hi, len_lo};
    u8 buf[MAX_FRAME_LEN + 3];
    memcpy(buf, header, 3);
    memcpy(buf + 3, payload, *payload_len);
    u8 calc_crc = crc8(buf, 3 + *payload_len);

    if (rx_crc != calc_crc)
        return -2;  /* CRC error */

    return 0;
}

static void send_frame(u8 cmd, const u8 *payload, u16 payload_len) {
    u8 header[3] = {cmd, (u8)(payload_len >> 8), (u8)(payload_len & 0xFF)};
    u8 buf[MAX_FRAME_LEN + 3];
    memcpy(buf, header, 3);
    memcpy(buf + 3, payload, payload_len);
    u8 frame_crc = crc8(buf, 3 + payload_len);

    uart_send_buf(header, 3);
    uart_send_buf(payload, payload_len);
    uart_send_byte(frame_crc);
}

/* ------------------------------------------------------------------ */
/* HMAC IP driver                                                      */
/* ------------------------------------------------------------------ */
static inline void hmac_write(u32 offset, u32 val) {
    Xil_Out32(HMAC_BASEADDR + offset, val);
}

static inline u32 hmac_read(u32 offset) {
    return Xil_In32(HMAC_BASEADDR + offset);
}

static void hmac_load_key(const u32 *key) {
    for (int i = 0; i < 8; i++)
        hmac_write(HMAC_KEY_BASE + i * 4, key[i]);
}

static void hmac_load_msg(const u8 *msg, u32 msg_len) {
    /* Write message length */
    hmac_write(HMAC_MSG_LEN, msg_len);

    /* Write message as 32-bit words (big-endian) */
    u32 num_words = (msg_len + 3) / 4;
    for (u32 i = 0; i < num_words; i++) {
        u32 word = 0;
        for (int j = 0; j < 4; j++) {
            u32 idx = i * 4 + j;
            word <<= 8;
            if (idx < msg_len)
                word |= msg[idx];
        }
        hmac_write(HMAC_MSG_BASE + i * 4, word);
    }
    /* Zero remaining words */
    for (u32 i = num_words; i < 16; i++)
        hmac_write(HMAC_MSG_BASE + i * 4, 0);
}

static void hmac_start(void) {
    hmac_write(HMAC_CTRL, HMAC_CTRL_START);
}

static void hmac_wait_done(void) {
    while (!(hmac_read(HMAC_STATUS) & HMAC_STATUS_DONE))
        ;
}

static void hmac_read_hash(u8 *hash) {
    for (int i = 0; i < 8; i++) {
        u32 word = hmac_read(HMAC_HASH_BASE + i * 4);
        hash[i * 4 + 0] = (word >> 24) & 0xFF;
        hash[i * 4 + 1] = (word >> 16) & 0xFF;
        hash[i * 4 + 2] = (word >> 8)  & 0xFF;
        hash[i * 4 + 3] = (word >> 0)  & 0xFF;
    }
}

/* ------------------------------------------------------------------ */
/* Authentication handler                                              */
/* ------------------------------------------------------------------ */
static void handle_auth_req(const u8 *nonce) {
    u8 msg[MSG_LEN];
    u8 hmac_result[HMAC_LEN];
    u8 resp_payload[AUTH_RESP_LEN];

    /* Build message: nonce(32) || battery_id(4) || voltage(2) */
    memcpy(msg, nonce, NONCE_LEN);
    memcpy(msg + NONCE_LEN, battery_id, BATTERY_ID_LEN);
    msg[NONCE_LEN + BATTERY_ID_LEN]     = (voltage_mv >> 8) & 0xFF;
    msg[NONCE_LEN + BATTERY_ID_LEN + 1] = voltage_mv & 0xFF;

    /* Load key and message into HMAC IP */
    hmac_load_key(default_key);
    hmac_load_msg(msg, MSG_LEN);

    /* Compute HMAC */
    hmac_start();
    hmac_wait_done();

    /* Read result */
    hmac_read_hash(hmac_result);

    /* Build response: battery_id(4) + voltage(2) + hmac(32) */
    memcpy(resp_payload, battery_id, BATTERY_ID_LEN);
    resp_payload[BATTERY_ID_LEN]     = (voltage_mv >> 8) & 0xFF;
    resp_payload[BATTERY_ID_LEN + 1] = voltage_mv & 0xFF;
    memcpy(resp_payload + BATTERY_ID_LEN + VOLTAGE_LEN, hmac_result, HMAC_LEN);

    send_frame(CMD_AUTH_RESP, resp_payload, AUTH_RESP_LEN);
}

/* ------------------------------------------------------------------ */
/* Main loop                                                           */
/* ------------------------------------------------------------------ */
int main(void) {
    uart_init();
    xil_printf("SeBatt PoC firmware v1.0\r\n");
    xil_printf("Battery ID: %02X%02X%02X%02X\r\n",
               battery_id[0], battery_id[1], battery_id[2], battery_id[3]);
    xil_printf("Waiting for commands...\r\n");

    u8 cmd;
    u8 payload[MAX_FRAME_LEN];
    u16 payload_len;

    while (1) {
        int rc = recv_frame(&cmd, payload, &payload_len);
        if (rc != 0) {
            xil_printf("Frame error: %d\r\n", rc);
            continue;
        }

        switch (cmd) {
            case CMD_AUTH_REQ:
                if (payload_len >= NONCE_LEN) {
                    handle_auth_req(payload);
                }
                break;

            case CMD_LOCK:
                locked = 1;
                xil_printf("Battery LOCKED\r\n");
                break;

            case CMD_UNLOCK:
                locked = 0;
                xil_printf("Battery UNLOCKED\r\n");
                break;

            case CMD_STATUS: {
                u8 status = locked;
                send_frame(CMD_STATUS, &status, 1);
                break;
            }

            default:
                xil_printf("Unknown cmd: 0x%02X\r\n", cmd);
                break;
        }
    }

    return 0;
}
