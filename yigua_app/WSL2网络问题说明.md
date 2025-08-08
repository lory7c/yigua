# 🔧 WSL2网络访问问题解决方案

## 🚨 问题原因

**为什么电脑能访问但手机不能？**

- `192.168.74.71` 是WSL2的**虚拟网络IP**，不是你Windows电脑的真实IP
- WSL2运行在虚拟机中，有自己独立的网络
- 手机需要访问**Windows主机的IP**，而不是WSL2的IP

```
手机 ❌──> WSL2 IP (192.168.74.71)  // 无法直接访问
手机 ✅──> Windows IP ──> WSL2 IP   // 需要端口转发
```

## 🎯 解决方案

### 方案1：使用自动修复脚本（推荐）

1. **右键** `fix_network.bat`
2. **选择** "以管理员身份运行"
3. **等待** 脚本自动配置
4. **获取** 正确的IP地址

### 方案2：手动配置

#### 步骤1：查看Windows真实IP
打开CMD，运行：
```cmd
ipconfig
```
找到 "无线局域网适配器 WLAN" 下的 IPv4 地址（如：192.168.1.100）

#### 步骤2：配置端口转发
管理员权限运行CMD：
```cmd
# 获取WSL2的IP
wsl hostname -I

# 设置端口转发（假设WSL2 IP是192.168.74.71）
netsh interface portproxy add v4tov4 listenport=8888 listenaddress=0.0.0.0 connectport=8888 connectaddress=192.168.74.71
```

#### 步骤3：开放防火墙
```cmd
netsh advfirewall firewall add rule name="易卦服务器" dir=in action=allow protocol=TCP localport=8888
```

## 📱 正确的访问方式

### 手机访问：
- ❌ 错误：`http://192.168.74.71:8888`（WSL2内部IP）
- ✅ 正确：`http://192.168.1.100:8888`（Windows主机IP）

### 电脑访问：
- ✅ `http://localhost:8888`
- ✅ `http://127.0.0.1:8888`
- ✅ `http://192.168.1.100:8888`

## 🔍 如何确认配置成功？

1. **查看端口转发规则**：
```cmd
netsh interface portproxy show all
```

2. **测试连接**：
- 电脑浏览器：http://localhost:8888
- 手机浏览器：http://[Windows IP]:8888

## ⚠️ 常见问题

### Q: 每次重启后失效？
A: 端口转发规则是持久的，但WSL2的IP可能变化。运行修复脚本即可。

### Q: 手机还是无法访问？
检查：
1. 手机和电脑是否在同一WiFi
2. Windows防火墙是否关闭或允许8888端口
3. 路由器是否开启了AP隔离

### Q: 提示需要管理员权限？
A: 右键脚本，选择"以管理员身份运行"

## 💡 永久解决方案

### 选项1：固定WSL2的IP
编辑 `.wslconfig` 文件，固定IP地址

### 选项2：使用Docker Desktop
Docker Desktop会自动处理网络问题

### 选项3：直接在Windows运行Node.js
不使用WSL2，直接在Windows安装Node.js

---

**记住**：问题的根源是WSL2的网络隔离，需要通过端口转发让外部设备访问！