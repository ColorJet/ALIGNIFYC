#include "alinify/printer/printer_interface.h"
#include "alinify/common/logger.h"
#include <Windows.h>

namespace alinify {
namespace printer {

PrinterInterface::PrinterInterface()
    : dll_handle_(nullptr)
    , send_image_func_(nullptr)
    , get_status_func_(nullptr)
    , initialized_(false) {
    status_ = {};
}

PrinterInterface::~PrinterInterface() {
    close();
}

StatusCode PrinterInterface::initialize(const std::string& dll_path,
                                        const std::string& config_file) {
    LOG_INFO("Initializing printer interface with DLL: ", dll_path);
    
    // Load DLL
    HMODULE dll = LoadLibraryA(dll_path.c_str());
    if (!dll) {
        LOG_ERROR("Failed to load printer DLL: ", dll_path);
        return StatusCode::ERROR_PRINTER_COMMUNICATION;
    }
    
    dll_handle_ = static_cast<void*>(dll);
    
    // Load function pointers
    send_image_func_ = reinterpret_cast<SendImageFunc>(
        GetProcAddress(dll, "SendImage"));
    
    get_status_func_ = reinterpret_cast<GetStatusFunc>(
        GetProcAddress(dll, "GetStatus"));
    
    if (!send_image_func_ || !get_status_func_) {
        LOG_ERROR("Failed to load required functions from printer DLL");
        close();
        return StatusCode::ERROR_PRINTER_COMMUNICATION;
    }
    
    initialized_ = true;
    status_.connected = true;
    
    LOG_INFO("Printer interface initialized successfully");
    return StatusCode::SUCCESS;
}

StatusCode PrinterInterface::sendImage(const Image<byte_t>& image) {
    if (!initialized_) {
        LOG_ERROR("Printer not initialized");
        return StatusCode::ERROR_PRINTER_COMMUNICATION;
    }
    
    LOG_INFO("Sending image to printer: ", image.width, "x", image.height);
    
    int result = send_image_func_(image.ptr(), image.width, image.height, image.channels);
    
    if (result != 0) {
        LOG_ERROR("Failed to send image to printer, error code: ", result);
        return StatusCode::ERROR_PRINTER_COMMUNICATION;
    }
    
    LOG_INFO("Image sent successfully");
    return StatusCode::SUCCESS;
}

bool PrinterInterface::isReady() const {
    return initialized_ && status_.connected && !status_.printing;
}

PrinterInterface::PrinterStatus PrinterInterface::getStatus() const {
    return status_;
}

void PrinterInterface::close() {
    if (dll_handle_) {
        FreeLibrary(static_cast<HMODULE>(dll_handle_));
        dll_handle_ = nullptr;
    }
    
    initialized_ = false;
    status_.connected = false;
}

} // namespace printer
} // namespace alinify
