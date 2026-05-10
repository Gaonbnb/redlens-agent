#include "device_loader.h"

#include <stdexcept>
#include <string>

namespace dcu::runtime {

DeviceLoader::DeviceLoader(std::string driver_version)
    : driver_version_(std::move(driver_version)) {}

bool DeviceLoader::probe_device() const {
    return driver_version_.starts_with("1.");
}

void DeviceLoader::initialize() {
    if (!probe_device()) {
        throw std::runtime_error("device init failed: driver/runtime version mismatch");
    }
}

}  // namespace dcu::runtime
