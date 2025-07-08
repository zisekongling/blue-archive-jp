from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import os
import traceback
import datetime
import pytz  # 用于时区处理

# 卡池类型分类规则
def get_pool_type(title):
    """根据卡池标题获取类型"""
    if "精选" in title:
        return "精选招募"
    elif "特选" in title:
        return "特选招募"
    elif "庆典" in title or "纪念" in title:
        return "庆典招募"
    elif "复刻" in title:
        return "复刻招募"
    elif "招募" in title:
        return "常规招募"
    return "其他招募"

def get_dynamic_cards():
    try:
        # 配置 Chrome 浏览器选项
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")
        
        # 自动管理 Chrome 驱动
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        target_url = "https://www.gamekee.com/ba/kachi/17"
        
        print("开始加载页面...")
        driver.get(target_url)
        
        # 等待页面加载
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "card-item"))
        )
        
        # 模拟滚动确保内容加载
        print("模拟滚动加载内容...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        time.sleep(3)  # 确保内容渲染完成
        
        # 获取卡片元素
        cards = driver.find_elements(By.CLASS_NAME, "card-item")
        print(f"找到 {len(cards)} 张卡片")
        
        # 分类存储卡池
        upcoming_pools = []  # 未开启卡池
        ongoing_pools = []   # 进行中卡池
        ended_pools = []     # 已结束卡池
        ended_groups = {}    # 按进度分组的已结束卡池
        
        # 提取卡片数据
        for i, card in enumerate(cards, 1):
            try:
                img_element = card.find_element(By.CSS_SELECTOR, ".img-box .pic")
                img_url = img_element.get_attribute("src")
                
                title = card.find_element(By.CLASS_NAME, "title").text
                
                # 安全获取描述
                try:
                    desc_element = card.find_element(By.CLASS_NAME, "desc")
                    desc = desc_element.text
                except:
                    desc = ""
                
                # 标签信息
                tags = [tag.text for tag in card.find_elements(By.CSS_SELECTOR, ".tag-list .tag")]
                
                # 状态信息
                status_element = card.find_element(By.CLASS_NAME, "current")
                current_status = status_element.text
                
                # 进度信息
                progress_element = card.find_element(By.CSS_SELECTOR, ".progess-box .txt")
                progress_text = progress_element.text
                
                # 获取卡池类型
                pool_type = get_pool_type(title)
                
                card_data = {
                    "title": title,
                    "description": desc,
                    "image_url": img_url,
                    "status": current_status,
                    "tags": tags,
                    "progress": progress_text,
                    "type": pool_type
                }
                
                # 根据状态分类
                if "未开启" in current_status:
                    upcoming_pools.append(card_data)
                elif "进行中" in current_status:
                    ongoing_pools.append(card_data)
                elif "已结束" in current_status:
                    ended_pools.append(card_data)
                    
                    # 按进度分组已结束卡池
                    if progress_text not in ended_groups:
                        ended_groups[progress_text] = []
                    ended_groups[progress_text].append(card_data)
                
                print(f"已解析卡片 {i}/{len(cards)} - 状态: {current_status}")
            except Exception as card_err:
                print(f"卡片解析错误: {str(card_err)[:100]}")
                continue
        
        # 选择一期已结束卡池（取最近的一期）
        recent_ended = []
        if ended_groups:
            # 获取最新的一期（假设第一个进度组是最新的）
            first_group = list(ended_groups.values())[0]
            recent_ended = first_group
            print(f"选择一期已结束卡池，包含 {len(recent_ended)} 个卡池")
        
        # 组合最终结果
        result_pools = upcoming_pools + ongoing_pools + recent_ended
        
        print(f"卡池统计: 未开启 {len(upcoming_pools)} 个, 进行中 {len(ongoing_pools)} 个, 已结束一期 {len(recent_ended)} 个")
        print(f"最终保留 {len(result_pools)} 个卡池信息")
        return result_pools
        
    except Exception as e:
        print(f"爬取过程发生错误: {str(e)}")
        traceback.print_exc()
        return []
        
    finally:
        if 'driver' in locals():
            driver.quit()
            print("浏览器已关闭")

if __name__ == "__main__":
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    # 执行爬取
    results = get_dynamic_cards()
    
    # 获取当前时间并转换为东八区时间
    utc_now = datetime.datetime.utcnow()
    beijing_tz = pytz.timezone('Asia/Shanghai')
    beijing_time = utc_now.replace(tzinfo=datetime.timezone.utc).astimezone(beijing_tz)
    crawl_time = beijing_time.isoformat()
    
    # 构建输出数据（包含顶层时间戳）
    output_data = {
        "crawl_time": crawl_time,  # 顶层时间戳（东八区时间）
        "pools": results           # 卡池列表
    }
    
    # 保存结果
    output_file = "data/game_pools.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存至: {os.path.abspath(output_file)}")
    print(f"爬取时间(东八区): {crawl_time}")
    print(f"提取卡池数量: {len(results)}")
    if results:
        print(f"第一个卡池: {results[0]['title']} - 类型: {results[0]['type']}")
