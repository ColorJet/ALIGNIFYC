#ifndef ALINIFY_PRINTER_PRINTER_INTERFACE_H
#define ALINIFY_PRINTER_PRINTER_INTERFACE_H

#include "alinify/common/types.h"
#include <string>

namespace alinify {
namespace printer {

/**
 * @brief Interface for printer DLL communication
 * 
 * Abstracts the printer hardware interface for sending
 * registered images to the printhead
 */
class PrinterInterface {
public:
    PrinterInterface();
    ~PrinterInterface();
    
    /**
     * @brief Initialize printer connection
     * @param dll_path Path to printer DLL
     * @param config_file Configuration file for printer
     */
    StatusCode initialize(const std::string& dll_path,
                         const std::string& config_file = "");
    
    /**
     * @brief Send image to printer
     * @param image RGB image to print
     */
    StatusCode sendImage(const Image<byte_t>& image);
    
    /**
     * @brief Check if printer is ready
     */
    bool isReady() const;
    
    /**
     * @brief Get printer status
     */
    struct PrinterStatus {
        bool connected;
        bool printing;
        int queue_size;
        std::string last_error;
    };
    
    PrinterStatus getStatus() const;
    
    /**
     * @brief Close printer connection
     */
    void close();
    
private:
    // DLL function pointers
    void* dll_handle_;
    
    // Function pointers to DLL functions
    using SendImageFunc = int(*)(const unsigned char*, int, int, int);
    using GetStatusFunc = int(*)();
    
    SendImageFunc send_image_func_;
    GetStatusFunc get_status_func_;
    
    bool initialized_;
    PrinterStatus status_;
};

} // namespace printer
} // namespace alinify

#endif // ALINIFY_PRINTER_PRINTER_INTERFACE_H
