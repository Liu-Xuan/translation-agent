#!/bin/zsh
# 清除代理环境变量
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY

# 验证环境清洁
env | grep -i proxy 