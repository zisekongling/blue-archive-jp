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

# 定义活动类型映射规则
def get_activity_types(title):
    """根据活动标题获取类型列表"""
    types = []
    
    # 规则匹配（注意顺序，确保优先匹配特定类型）
    if "2倍" in title or "3倍" in title:
        types.append("资源翻倍")
    if "登入活动" in title:
        types.append("签到")
    if "制约解除决战" in title:
        types.append("制约解除决战")
    if "[活动]" in title:
        types.append("活动")
    if "总力战" in title:
        types.append("总力战")
    if "招募100次" in title:
        types.append("庆典")
    if "大决战" in title:
        types.append("大决战")
    if "综合战术考试" in title:
        types.append("考试")
    if "[迷你活动]" in title:
        types.append("长草活动")
    if "复刻" in title:
        types.append("复刻")
    
    # 如果没有匹配到任何类型，添加默认类型
    if not types:
        types.append("其他")
    
    return types

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

        # 初始化状态分类列表
        ongoing_cards = []  # 进行中活动
        upcoming_cards = []  # 未开启活动
        ended_cards = []  # 已结束活动
        
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
                
                # 获取活动类型
                activity_types = get_activity_types(title)
                
                card_item = {
                    "title": title,
                    "description": desc,
                    "image_url": img_url,
                    "status": current_status,
                    "progress": progress_text,
                    "type": activity_types  # 添加类型字段
                }
                
                # 根据状态分类
                if "进行中" in current_status:
                    ongoing_cards.append(card_item)
                elif "未开启" in current_status:
                    upcoming_cards.append(card_item)
                elif "已结束" in current_status:
                    ended_cards.append(card_item)
                
            except Exception as card_err:
                logging.error(f"卡片解析失败: {str(card_err)[:100]}")
                continue
        
        # 组合最终结果：所有进行中+未开启活动 + 最新的5个已结束活动
        result_cards = ongoing_cards + upcoming_cards + ended_cards[:5]
        
        logging.info(f"活动统计: 进行中 {len(ongoing_cards)} 个, 未开启 {len(upcoming_cards)} 个, 已结束 {len(ended_cards)} 个")
        logging.info(f"最终保留 {len(result_cards)} 张卡片信息")
        return result_cards
        
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
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "activity_cards.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logging.info(f"结果已保存至: {os.path.abspath(output_file)}")
    if results:
        logging.info(f"第一张卡片: {results[0]['title']} - 类型: {results[0]['type']}")
