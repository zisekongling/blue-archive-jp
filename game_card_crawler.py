from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import json
import os
import logging
import time

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
        
        # 配置浏览器选项
        edge_options = Options()
        
        if on_github:
            logging.info("在 GitHub Actions 环境中运行")
            edge_options.add_argument("--headless=new")  # 无头模式
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--disable-dev-shm-usage")  # 避免容器内存问题
            edge_options.add_argument("--no-sandbox")  # 禁用沙盒
            edge_options.add_argument("--disable-extensions")  # 禁用扩展
            edge_options.add_argument("--remote-debugging-port=9222")  # 远程调试端口
            
            # 在 GitHub Actions 中直接使用系统安装的 Edge
            driver_path = "/usr/bin/microsoft-edge"
            driver = webdriver.Edge(
                service=Service(driver_path),
                options=edge_options
            )
        else:
            logging.info("在本地环境中运行")
            edge_options.add_argument("--headless=new")  # 无头模式
            # 其他本地特定设置
            
            # 自动管理 Edge 驱动
            driver = webdriver.Edge(
                service=Service(EdgeChromiumDriverManager().install()),
                options=edge_options
            )

        card_data = []
        target_url = "https://www.gamekee.com/ba/kachi/17"
        logging.info(f"访问目标页面: {target_url}")
        driver.get(target_url)
        
        # 显式等待卡片加载
        wait = WebDriverWait(driver, 25)  # GitHub Actions 需要更长时间
        logging.info("等待卡片容器加载...")
        card_container = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "card-item"))
        )
        
        # 滚动到容器确保完全加载
        driver.execute_script("arguments[0].scrollIntoView();", card_container)
        time.sleep(3)  # 确保内容加载
        
        # 获取所有卡片元素
        cards = driver.find_elements(By.CLASS_NAME, "card-item")
        logging.info(f"发现 {len(cards)} 个卡片元素")
        
        # 提取卡片数据
        for card in cards:
            try:
                img_element = card.find_element(By.CSS_SELECTOR, ".img-box .pic")
                img_url = img_element.get_attribute("src")
                title = card.find_element(By.CLASS_NAME, "title").text
                
                desc_element = card.find_element(By.CLASS_NAME, "desc")
                desc = desc_element.text if desc_element else ""
                
                tags = [tag.text for tag in card.find_elements(By.CSS_SELECTOR, ".tag-list .tag")]
                current_status = card.find_element(By.CLASS_NAME, "current").text
                progress_text = card.find_element(By.CSS_SELECTOR, ".progess-box .txt").text
                
                card_data.append({
                    "title": title,
                    "description": desc,
                    "image_url": img_url,
                    "status": current_status,
                    "tags": tags,
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
        driver.quit()
        logging.info("浏览器已关闭")

if __name__ == "__main__":
    # 执行爬取
    results = get_dynamic_cards()
    
    # 保存结果到JSON文件
    output_file = "game_cards.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logging.info(f"结果已保存至: {os.path.abspath(output_file)}")
    if results:
        logging.info(f"第一张卡片: {results[0]['title']}")
