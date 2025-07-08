from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import json
import time
import os

def get_dynamic_cards():
    # 配置Edge浏览器选项
    edge_options = Options()
    edge_options.add_argument("--headless=new")  # 无头模式
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.50")
    
    # 自动管理Edge驱动
    driver = webdriver.Edge(
        service=Service(EdgeChromiumDriverManager().install()),
        options=edge_options
    )
    
    card_data = []
    
    try:
        # 访问目标URL
        target_url = "https://www.gamekee.com/ba/kachi/17"
        driver.get(target_url)
        print(f"正在加载页面: {target_url}...")
        
        # 显式等待卡片容器加载（需根据实际页面调整）
        wait = WebDriverWait(driver, 20)
        card_container = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "card-item"))
        )
        
        # 滚动到容器确保完全加载
        driver.execute_script("arguments[0].scrollIntoView();", card_container)
        time.sleep(2)  # 确保内容加载
        
        # 获取所有卡片元素
        cards = driver.find_elements(By.CLASS_NAME, "card-item")
        print(f"发现 {len(cards)} 个卡片元素")
        
        # 提取卡片数据
        for card in cards:
            try:
                # 图片URL
                img_element = card.find_element(By.CSS_SELECTOR, ".img-box .pic")
                img_url = img_element.get_attribute("src")
                
                # 标题
                title = card.find_element(By.CLASS_NAME, "title").text
                
                # 描述
                desc_element = card.find_element(By.CLASS_NAME, "desc")
                desc = desc_element.text if desc_element else ""
                
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
                    "progress": progress_text
                })
            except Exception as card_err:
                print(f"卡片解析失败: {str(card_err)[:100]}")
                continue
        
        print(f"成功提取 {len(card_data)} 张卡片信息")
        return card_data
        
    except Exception as e:
        print(f"爬取过程发生错误: {str(e)}")
        return []
        
    finally:
        driver.quit()
        print("浏览器已关闭")

if __name__ == "__main__":
    # 执行爬取
    results = get_dynamic_cards()
    
    # 保存结果到JSON文件
    output_file = "game_cards.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存至: {os.path.abspath(output_file)}")
    print("以下是第一张卡片示例:")
    if results:
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
