from iFinDPy import *
import pandas as pd

# ==========================================
# FactorX Pro - iFinD 本地数据嗅探器 (测试版)
# ==========================================

def test_ifind_connection():
    print("正在尝试唤醒 iFinD 终端底层接口...")
    
    # 1. 登录 iFinD (如果你的电脑已经打开了同花顺终端，账号密码可留空或填你自己的)
    # 注意：首次运行可能需要输入账号密码
    login_result = THS_iFinDLogin("你的账号", "你的密码") 
    
    if login_result != 0:
        print("❌ 登录失败！请检查 iFinD 客户端是否开启，或账号密码是否正确。")
        return
    else:
        print("✅ iFinD 接口接驳成功！")

    # 2. 尝试提取贵州茅台的近 10 天行情数据作为测试
    test_symbol = "600519.SH"
    print(f"正在提取 {test_symbol} 测试数据...")
    
    # THS_HistoryQuotes 是拉取历史 K 线的核心函数
    data = THS_HistoryQuotes(test_symbol, "open,high,low,close,volume", "period:D,cps:1,Y:Y,Fill:Blank", "2024-05-01", "2026-05-07")
    
    if data.errorcode == 0:
        df = data.data
        print("✅ 数据提取成功，数据样本如下：")
        print(df.tail())
    else:
        print(f"❌ 数据提取失败: {data.errmsg}")

    # 3. 断开连接，释放资源
    THS_iFinDLogout()
    print("已安全断开 iFinD 连接。")

if __name__ == "__main__":
    test_ifind_connection()
