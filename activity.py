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
import re

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

def parse_time_range(progress_text, crawl_time_dt):
    """
    解析时间范围字符串，返回开始和结束时间的ISO格式字符串
    支持两种格式：
    1. 相对时间："还剩下X天Y小时"
    2. 绝对时间："YYYY/MM/DD-YYYY/MM/DD" 或 "YYYY/MM/DD HH:MM-YYYY/MM/DD HH:MM"
    """
    # 处理相对时间格式（如"还剩下26天21小时"）
    if "还剩下" in progress_text:
        try:
            # 提取天数和小时数
            match = re.search(r'还剩下(\d+)天(\d+)小时', progress_text)
            if match:
                days = int(match.group(1))
                hours = int(match.group(2))
                
                # 计算结束时间
                time_delta = datetime.timedelta(days=days, hours=hours)
                end_time = crawl_time_dt + time_delta
                
                # 精确到小时
                end_time = end_time.replace(minute=0, second=0, microsecond=0)
                return None, end_time.isoformat()
        except Exception as e:
            logging.error(f"解析相对时间失败: {progress_text}, 错误: {str(e)}")
            return None, None
    
    # 处理绝对时间格式
    if "-" in progress_text:
        try:
            # 分割时间范围字符串
            parts = progress_text.split("-")
            if len(parts) == 2:
                start_str, end_str = parts
                
                # 统一格式化日期字符串
                start_str = start_str.strip().replace("/", "-")
                end_str = end_str.strip().replace("/", "-")
                
                # 检查是否包含小时分钟信息
                if ":" in start_str:
                    # 包含小时分钟
                    start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M")
                    end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M")
                else:
                    # 仅包含日期，设置时间为0点
                    start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d")
                    end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d")
                
                # 添加UTC+8时区信息
                tz = datetime.timezone(datetime.timedelta(hours=8))
                start_dt = start_dt.replace(tzinfo=tz)
                end_dt = end_dt.replace(tzinfo=tz)
                
                # 精确到小时
                start_dt = start_dt.replace(minute=0, second=0, microsecond=0)
                end_dt = end_dt.replace(minute=0, second=0, microsecond=0)
                
                return start_dt.isoformat(), end_dt.isoformat()
        except Exception as e:
            logging.error(f"解析绝对时间失败: {progress_text}, 错误: {str(e)}")
            return None, None
    
    # 无法识别的格式
    logging.warning(f"无法解析的时间格式: {progress_text}")
    return None, None

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
        
        target_url = "https://www.gamekee.com/ba/huodong/15"  # 正确的活动URL
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
                    "tags": activity_types  # 保留类型字段
                }
                
                # 根据状态分类
                if "进行中" in current_status:
                    ongoing_cards.append(card_item)
                elif "未开始" in current_status:
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
    
    # 添加爬取时间（当前时间+8小时），精确到小时
    tz = datetime.timezone(datetime.timedelta(hours=8))
    crawl_time_dt = datetime.datetime.now(tz)
    crawl_time_dt = crawl_time_dt.replace(minute=0, second=0, microsecond=0)
    crawl_time = crawl_time_dt.isoformat()
    
    # 处理卡片数据：添加时间字段，保留tags字段
    processed_results = []
    for card in results:
        # 解析时间范围
        start_time, end_time = parse_time_range(card["progress"], crawl_time_dt)
        
        # 创建新卡片对象，保留tags字段
        new_card = {
            "title": card["title"],
            "description": card["description"],
            "image_url": card["image_url"],
            "progress": card["progress"],
            "tags": card["tags"],  # 保留tags字段
            "start_time": start_time,
            "end_time": end_time
        }
        processed_results.append(new_card)
    
    # 构建最终输出结构
    final_output = {
        "crawl_time": crawl_time,
        "activities": processed_results
    }
    
    # 保存结果到JSON文件
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "activity_cards.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    
    logging.info(f"结果已保存至: {os.path.abspath(output_file)}")
    if processed_results:
        logging.info(f"第一张卡片: {processed_results[0]['title']} - 类型: {processed_results[0]['tags']} - 结束时间: {processed_results[0]['end_time']}")
