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
import datetime  # 添加 datetime 模块

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
        
        card_data = []
        target_url = "https://www.gamekee.com/ba/kachi/17"
        
        print("开始加载页面...")
        driver.get(target_url)
        
        # 等待页面加载
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "card-item"))
        )
        
        # 模拟滚动确保内容加载
        print("模拟滚动加载内容...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # 获取卡片元素
        cards = driver.find_elements(By.CLASS_NAME, "card-item")
        print(f"找到 {len(cards)} 张卡片")
        
        # 获取当前时间（ISO格式）
        crawl_time = datetime.datetime.now().isoformat()
        
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
                current_status = card.find_element(By.CLASS_NAME, "current").text
                
                # 进度信息
                progress_text = card.find_element(By.CSS_SELECTOR, ".progess-box .txt").text
                
                card_data.append({
                    "title": title,
                    "description": desc,
                    "image_url": img_url,
                    "status": current_status,
                    "tags": tags,
                    "progress": progress_text,
                    "crawl_time": crawl_time  # 添加爬取时间到每条记录
                })
                print(f"已解析卡片 {i}/{len(cards)}")
            except Exception as card_err:
                print(f"卡片解析错误: {str(card_err)[:100]}")
                continue
        
        print(f"成功提取 {len(card_data)} 张卡片")
        return card_data, crawl_time  # 返回数据和时间
        
    except Exception as e:
        print(f"爬取过程发生错误: {str(e)}")
        traceback.print_exc()
        return [], datetime.datetime.now().isoformat()
        
    finally:
        if 'driver' in locals():
            driver.quit()
            print("浏览器已关闭")

if __name__ == "__main__":
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    # 执行爬取
    results, crawl_time = get_dynamic_cards()
    
    # 构建输出数据（包含顶层时间戳）
    output_data = {
        "crawl_time": crawl_time,  # 顶层时间戳
        "cards": results           # 卡片列表
    }
    
    # 保存结果
    output_file = "data/game_cards.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存至: {os.path.abspath(output_file)}")
    print(f"爬取时间: {crawl_time}")
    print(f"提取卡片数量: {len(results)}")
