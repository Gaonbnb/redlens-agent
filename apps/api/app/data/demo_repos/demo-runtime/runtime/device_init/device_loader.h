#pragma once

#include <string>

namespace dcu::runtime {

class DeviceLoader {
 public:
    explicit DeviceLoader(std::string driver_version);
    bool probe_device() const;
    void initialize();

 private:
    std::string driver_version_;
};

}  // namespace dcu::runtime
