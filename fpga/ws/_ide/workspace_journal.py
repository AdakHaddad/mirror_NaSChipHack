# 2026-10-18T21:34:57.392292
import vitis

client = vitis.create_client()
client.set_workspace(path="ws")

platform = client.create_platform_component(name = "platform",hw_design = "$COMPONENT_LOCATION/../../basys_3/vivado_proj/sebatt_bd_wrapper.xsa",os = "standalone",cpu = "microblaze_riscv_0",domain_name = "standalone_microblaze_riscv_0")

platform = client.get_component(name="platform")
status = platform.update_hw(hw_design = "$COMPONENT_LOCATION/../../basys_3/vivado_proj/sebatt_bd_wrapperbasys3.xsa")

platform = client.create_platform_component(name = "platform_basys3",hw_design = "$COMPONENT_LOCATION/../../basys_3/vivado_proj/sebatt_bd_wrapperbasys3.xsa",os = "standalone",cpu = "microblaze_riscv_0",domain_name = "standalone_microblaze_riscv_0")

comp = client.create_app_component(name="app_component",platform = "$COMPONENT_LOCATION/../platform_basys3/export/platform_basys3/platform_basys3.xpfm",domain = "standalone_microblaze_riscv_0")

comp = client.get_component(name="app_component")
status = comp.import_files(from_loc="", files=["/home/muqtada/Documents/sebatt/fpga/fw/sebatt_fw.c"])

platform = client.get_component(name="platform_basys3")
status = platform.build()

comp.build()

status = platform.build()

comp.build()

vitis.dispose()

