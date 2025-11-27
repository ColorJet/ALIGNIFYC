#ifndef ALINIFY_COMMON_LOGGER_H
#define ALINIFY_COMMON_LOGGER_H

// Prevent Windows macro conflicts
#ifndef NOMINMAX
#define NOMINMAX
#endif
#undef ERROR  // Undefine Windows ERROR macro

#include "types.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <mutex>
#include <memory>

namespace alinify {

class Logger {
public:
    static Logger& getInstance() {
        static Logger instance;
        return instance;
    }
    
    void setLogLevel(LogLevel level) {
        std::lock_guard<std::mutex> lock(mutex_);
        log_level_ = level;
    }
    
    void setLogFile(const std::string& filename) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (file_.is_open()) {
            file_.close();
        }
        file_.open(filename, std::ios::out | std::ios::app);
        if (!file_.is_open()) {
            std::cerr << "Failed to open log file: " << filename << std::endl;
        }
    }
    
    template<typename... Args>
    void log(LogLevel level, Args&&... args) {
        if (level < log_level_) return;
        
        std::lock_guard<std::mutex> lock(mutex_);
        
        std::ostringstream oss;
        oss << "[" << getTimestamp() << "] ";
        oss << "[" << levelToString(level) << "] ";
        ((oss << std::forward<Args>(args)), ...);
        oss << std::endl;
        
        std::string message = oss.str();
        
        // Console output
        if (level >= LogLevel::ERROR) {
            std::cerr << message;
        } else {
            std::cout << message;
        }
        
        // File output
        if (file_.is_open()) {
            file_ << message;
            file_.flush();
        }
    }
    
    template<typename... Args>
    void debug(Args&&... args) {
        log(LogLevel::DEBUG, std::forward<Args>(args)...);
    }
    
    template<typename... Args>
    void info(Args&&... args) {
        log(LogLevel::INFO, std::forward<Args>(args)...);
    }
    
    template<typename... Args>
    void warning(Args&&... args) {
        log(LogLevel::WARNING, std::forward<Args>(args)...);
    }
    
    template<typename... Args>
    void error(Args&&... args) {
        log(LogLevel::ERROR, std::forward<Args>(args)...);
    }
    
    template<typename... Args>
    void critical(Args&&... args) {
        log(LogLevel::CRITICAL, std::forward<Args>(args)...);
    }
    
private:
    Logger() : log_level_(LogLevel::INFO) {}
    ~Logger() {
        if (file_.is_open()) {
            file_.close();
        }
    }
    
    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;
    
    std::string getTimestamp() {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()) % 1000;
        
        char buffer[64];
        std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", std::localtime(&time));
        
        std::ostringstream oss;
        oss << buffer << "." << std::setfill('0') << std::setw(3) << ms.count();
        return oss.str();
    }
    
    std::string levelToString(LogLevel level) {
        switch(level) {
            case LogLevel::DEBUG: return "DEBUG";
            case LogLevel::INFO: return "INFO";
            case LogLevel::WARNING: return "WARNING";
            case LogLevel::ERROR: return "ERROR";
            case LogLevel::CRITICAL: return "CRITICAL";
            default: return "UNKNOWN";
        }
    }
    
    LogLevel log_level_;
    std::ofstream file_;
    std::mutex mutex_;
};

// Convenience macros
#define LOG_DEBUG(...) alinify::Logger::getInstance().debug(__VA_ARGS__)
#define LOG_INFO(...) alinify::Logger::getInstance().info(__VA_ARGS__)
#define LOG_WARNING(...) alinify::Logger::getInstance().warning(__VA_ARGS__)
#define LOG_ERROR(...) alinify::Logger::getInstance().error(__VA_ARGS__)
#define LOG_CRITICAL(...) alinify::Logger::getInstance().critical(__VA_ARGS__)

} // namespace alinify

#endif // ALINIFY_COMMON_LOGGER_H
