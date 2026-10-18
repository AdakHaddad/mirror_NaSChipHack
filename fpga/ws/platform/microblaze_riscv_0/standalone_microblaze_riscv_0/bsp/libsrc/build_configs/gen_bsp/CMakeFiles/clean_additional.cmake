# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "")
  file(REMOVE_RECURSE
  "/home/muqtada/Documents/sebatt/fpga/ws/platform/microblaze_riscv_0/standalone_microblaze_riscv_0/bsp/include/sleep.h"
  "/home/muqtada/Documents/sebatt/fpga/ws/platform/microblaze_riscv_0/standalone_microblaze_riscv_0/bsp/include/xiltimer.h"
  "/home/muqtada/Documents/sebatt/fpga/ws/platform/microblaze_riscv_0/standalone_microblaze_riscv_0/bsp/include/xtimer_config.h"
  "/home/muqtada/Documents/sebatt/fpga/ws/platform/microblaze_riscv_0/standalone_microblaze_riscv_0/bsp/lib/libxiltimer.a"
  )
endif()
