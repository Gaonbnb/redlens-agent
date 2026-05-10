#include "device_loader.h"

#include <iostream>

namespace dcu::runtime {

int hipInit(const char* driver_version) {
    DeviceLoader loader(driver_version);
    loader.initialize();
    std::cout << "runtime init success" << std::endl;
    return 0;
}

}  // namespace dcu::runtime
