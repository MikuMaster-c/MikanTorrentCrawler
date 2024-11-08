import os
import re
import requests
import time
from lxml import etree
from fake_useragent import UserAgent
import urllib3
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# 网站url
class Mikan(object):

    def __init__(self,
                 use_proxy=False,
                 proxy_host='',
                 proxy_port=0,
                 proxy_username='',
                 proxy_pwd='',
                 max_workers=10):

        self.url = "https://mikan.hakurei.red/Home/Classic/{}"
        ua = UserAgent()
        self.headers = {
            'User-Agent': ua.random,  # 随机User-Agent
        }

        self.session = requests.Session()
        self.session.verify = False  # 禁用SSL验证

        # 配置代理
        if use_proxy:
            proxymeta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
                "host": proxy_host,
                "port": proxy_port,
                "user": proxy_username,
                "pass": proxy_pwd,
            }

            self.proxies = {
                'http': proxymeta,
                'https': proxymeta,
            }
        else:
            self.proxies = {}

        # 保存已爬取页面到日志
        self.log_file = "爬取日志.txt"
        self.request_count = 0
        self.start_time = time.time()

        # 每页爬取时长
        self.page_start_time = time.time()
        self.page_times = []

        # 流量
        self.total_downloaded = 0
        self.last_report_time = time.time()
        self.last_downloaded = 0

        # 线程数
        self.max_workers = max_workers

    def get_page(self, url, retries=3, delay=1):
        attempt = 0
        while attempt < retries:
            try:
                req = self.session.get(url=url, headers=self.headers, proxies=self.proxies)
                req.raise_for_status()  # 如果请求失败,抛出异常
                self.request_count += 1
                self.total_downloaded += len(req.content)
                return req.content
            except requests.exceptions.RequestException as e:
                attempt += 1
                print(f"请求失败（{attempt}/{retries}) - 错误信息: {e}")
                if attempt < retries:
                    print(f"等待 {delay} 秒后重试...")
                    time.sleep(delay)
                else:
                    print(f"已重试 {retries} 次,放弃请求 {url}")
                    return None

    def page_page(self, html):
        parse_html = etree.HTML(html)
        one = parse_html.xpath('//tbody//tr//td[3]/a/@href')

        # 线程池
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for li in one:
                yr = "https://mikan.hakurei.red/" + li
                futures.append(executor.submit(self.process_page, yr))

            for future in as_completed(futures):
                future.result()

    def process_page(self, yr):
        # 下载重试
        html2 = self.get_page(yr, retries=3, delay=2)
        if not html2:
            print(f"页面 {yr} 下载失败，跳过")
            return

        parse_html2 = etree.HTML(html2)

        tow = parse_html2.xpath('//body')
        for i in tow:
            episode_title = i.xpath('.//p[@class="episode-title"]//text()')

            if episode_title:
                four = episode_title[0].strip()
                fif = i.xpath('.//div[@class="leftbar-nav"]/a[1]/@href')[0].strip()
                t = "https://mikan.hakurei.red/" + fif
                print(t)

                # 清理非法字符
                safe_name = re.sub(r'[\\/:*?"<>|\n\r]', '_', four)

                dirname = os.path.join('./种子/', safe_name + '.torrent')

                os.makedirs(os.path.dirname(dirname), exist_ok=True)
                print(f"文件路径: {dirname}")

                html3 = self.get_page(t, retries=3, delay=2)
                if not html3:  # 如果下载失败就跳过当前文件
                    print(f"文件 {t} 下载失败，跳过")
                    return

                # 获取二进制数据,写入文件
                try:
                    with open(dirname, 'wb') as f:
                        f.write(html3)
                        print(f"\n{four} 下载成功!!")
                except Exception as e:
                    print(f"保存文件失败: {e}")
            else:
                print("没有找到有效的 {episode-title} ,跳过这一项")

    def save_log(self, page):
        # 保存日志
        with open(self.log_file, 'a', encoding='utf-8') as log:
            log.write(f"{page}\n")
        print(f"已保存第 {page} 页为日志")

    def load_log(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as log:
                return [int(line.strip()) for line in log.readlines()]
        return []

    def report_rps(self):
        # 统计RPS和流量
        while True:
            time.sleep(10)
            elapsed_time = time.time() - self.start_time
            rps = self.request_count / elapsed_time if elapsed_time > 0 else 0
            print(f"当前RPS: {rps:.2f} 请求/秒")

            # 10秒平均流量
            now = time.time()
            time_diff = now - self.last_report_time
            downloaded = self.total_downloaded - self.last_downloaded
            download_speed = (downloaded / time_diff) / (1024 * 1024)  # 转换成MB/s
            print(f"最近10秒的平均流量: {download_speed:.2f} MB/s")

            self.last_report_time = now
            self.last_downloaded = self.total_downloaded

    def calculate_avg_page_time(self):
        if len(self.page_times) >= 3:
            avg_time = sum(self.page_times[-3:]) / 3
            print(f"最近3页的平均爬取时长: {avg_time:.2f}秒")

    def main(self):
        # 并行数
        max_workers_input = int(input("输入最大并行数: ").strip())

        # 输入是否使用代理
        use_proxy_input = input("是否使用代理? (y/n): ").strip().lower()
        use_proxy = use_proxy_input == 'y'

        if use_proxy:
            proxy_host = input("输入代理host: ").strip()
            proxy_port = int(input("输入代理port: ").strip())
            proxy_username = input("输入代理用户名 (若无则留空): ").strip()
            proxy_pwd = input("输入代理密码 (若无则留空): ").strip()
            siper = Mikan(use_proxy=True,
                          proxy_host=proxy_host,
                          proxy_port=proxy_port,
                          proxy_username=proxy_username,
                          proxy_pwd=proxy_pwd,
                          max_workers=max_workers_input)

        else:
            siper = Mikan(use_proxy=False, max_workers=max_workers_input)

        stat = int(input("start:"))
        end = int(input("  end:"))

        crawled_pages = self.load_log()
        start_page = max(stat, max(crawled_pages, default=stat))

        # 启动RPS和流量报告线程
        threading.Thread(target=siper.report_rps, daemon=True).start()

        for page in range(start_page, end + 1):
            page_start = time.time()
            url = self.url.format(page)
            print(url)
            html = siper.get_page(url)
            if not html:  # 获取页面失败,跳过当前页
                print(f"页面 {url} 下载失败,跳过...")
                continue
            siper.page_page(html)
            siper.save_log(page)  # 保存爬取的页面到日志

            page_end = time.time()
            page_time = page_end - page_start
            siper.page_times.append(page_time)

            if len(siper.page_times) % 3 == 0:
                siper.calculate_avg_page_time()

            print("--------------------第%s页爬取成功!--------------------" % page)
            time.sleep(random.uniform(0.2, 1.5))


if __name__ == '__main__':
    Siper = Mikan()
    Siper.main()
