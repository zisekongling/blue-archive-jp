from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import os
import logging
import time
import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

def get_dynamic_cards():
    try:
        # GitHub Actions 环境设置
        on_github = os.getenv("GITHUB_ACTIONS") == "true"
        
        # 配置浏览器选项 - 修改为Chrome
        chrome_options = Options()
        
        if on_github:
            logging.info("在 GitHub Actions 环境中运行")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")
            
            # 使用自动安装的Chrome驱动
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
        else:
            logging.info("在本地环境中运行")
            chrome_options.add_argument("--headless=new")
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )

        card_data = []
        target_url = "https://www.gamekee.com/ba/huodong/17"  # 正确的活动URL
        logging.info(f"访问目标页面: {target_url}")
        driver.get(target_url)
        
        # 显式等待卡片加载
        wait = WebDriverWait(driver, 25)
        logging.info("等待卡片容器加载...")
        wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "card-item"))
        )
        
        # 滚动页面确保加载所有动态内容
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        time.sleep(2)  # 确保内容渲染完成
        
        # 获取所有卡片元素
        cards = driver.find_elements(By.CLASS_NAME, "card-item")
        logging.info(f"发现 {len(cards)} 个卡片元素")
        
        # 提取卡片数据
        for card in cards:
            try:
                # 图片元素
                img_element = card.find_element(By.CSS_SELECTOR, ".left img.pic")
                img_url = img_element.get_attribute("src")
                
                # 标题
                title = card.find_element(By.CSS_SELECTOR, ".right .title").text
                
                # 描述
                desc_element = card.find_elements(By.CSS_SELECTOR, ".right .desc")
                desc = desc_element[0].text if desc_element else ""
                
                # 状态
                status_element = card.find_element(By.CSS_SELECTOR, ".status-txt")
                current_status = status_element.text
                
                # 进度
                progress_element = card.find_element(By.CSS_SELECTOR, ".progess-box .txt")
                progress_text = progress_element.text
                
                card_data.append({
                    "title": title,
                    "description": desc,
                    "image_url": img_url,
                    "status": current_status,
                    "progress": progress_text
                })
            except Exception as card_err:
                logging.error(f"卡片解析失败: {str(card_err)[:100]}")
                continue
        
        logging.info(f"成功提取 {len(card_data)} 张卡片信息")
        return card_data
        
    except Exception as e:
        logging.error(f"爬取过程发生错误: {str(e)}")
        return []
    finally:
        if driver:
            driver.quit()
            logging.info("浏览器已关闭")

if __name__ == "__main__":
    # 执行爬取
    results = get_dynamic_cards()
    
    # 保存结果到JSON文件
    output_file = "data/activity_cards.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logging.info(f"结果已保存至: {os.path.abspath(output_file)}")
    if results:
        logging.info(f"第一张卡片: {results[0]['title']}")
