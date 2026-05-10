#include <string>

namespace dcu::framework {

extern int hipInit(const char* driver_version);

bool start_pytorch_session(const std::string& driver_version) {
    return hipInit(driver_version.c_str()) == 0;
}

}  // namespace dcu::framework
