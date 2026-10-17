# Makefile for cocotb simulation
# Usage:
#   make sha256    — run SHA-256 core tests
#   make hmac      — run HMAC-SHA-256 tests
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

# ---- All ----
all: sha256 hmac

clean:
	rm -rf sim_build results.xml __pycache__ *.vcd

.PHONY: sha256 hmac all clean
