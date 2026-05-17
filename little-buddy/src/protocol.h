#pragma once

/** 处理一行 UTF-8（已去掉换行）。成功解析出可显示文案返回 true。 */
bool protocolHandleLine(const char *line);
