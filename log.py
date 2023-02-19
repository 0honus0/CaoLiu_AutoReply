import logging.config ,sys

def outputLog(projectName):
    log = logging.getLogger(f"{projectName}")
    log.setLevel(level=logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]\t%(message)s')
    # 输出日志到终端
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.formatter = formatter
    log.addHandler(console_handler)
    #输出日志到文件
    file_handler = logging.FileHandler(f'{projectName}.log', encoding='utf-8')
    file_handler.formatter = formatter
    file_handler.level = logging.INFO
    log.addHandler(file_handler)
    return log