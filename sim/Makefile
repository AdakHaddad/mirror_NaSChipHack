# Makefile for cocotb simulation
# Usage:
#   make sha256    — run SHA-256 core tests
#   make hmac      — run HMAC-SHA-256 tests
#   make ads1115   — run ADS1115 I2C controller tests
#   make auth      — run UART/auth_ctrl/HMAC integration tests
#   make all       — run all tests

TOPLEVEL_LANG = verilog
SIM ?= icarus

# Paths
RTL_DIR = ../rtl
VERILOG_SOURCES =

# ---- SHA-256 core test ----
sha256: export TOPLEVEL = sha256_core
sha256: export MODULE = test_sha256
sha256: export VERILOG_SOURCES = $(RTL_DIR)/sha256_core.v
sha256:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim

# ---- HMAC-SHA-256 test ----
hmac: export TOPLEVEL = hmac_sha256
hmac: export MODULE = test_hmac
hmac: export VERILOG_SOURCES = $(RTL_DIR)/sha256_core.v $(RTL_DIR)/hmac_sha256.v
hmac:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim

# ---- ADS1115 I2C controller test ----
ads1115: export TOPLEVEL = ads1115_ctrl
ads1115: export MODULE = test_ads1115
ads1115: export COMPILE_ARGS = -DSIMULATION
ads1115: export VERILOG_SOURCES = $(RTL_DIR)/i2c_master.v $(RTL_DIR)/ads1115_ctrl.v
ads1115:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim

# ---- UART + auth_ctrl + HMAC integration test ----
auth: export TOPLEVEL = tb_auth
auth: export MODULE = test_auth_ctrl
auth: export PYTHONPATH = $(CURDIR)/..
auth: export VERILOG_SOURCES = $(RTL_DIR)/uart_if.v $(RTL_DIR)/axil_master.v \
	$(RTL_DIR)/sha256_core.v $(RTL_DIR)/hmac_sha256.v $(RTL_DIR)/auth_ctrl.v \
	$(CURDIR)/tb_auth.v
auth:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim

# ---- All ----
# Icarus reuses sim_build/sim.vvp across targets, so clean between runs.
all:
	$(MAKE) clean
	$(MAKE) sha256
	$(MAKE) clean
	$(MAKE) hmac
	$(MAKE) clean
	$(MAKE) ads1115
	$(MAKE) clean
	$(MAKE) auth

clean:
	rm -rf sim_build results.xml __pycache__ *.vcd

.PHONY: sha256 hmac ads1115 auth all clean
