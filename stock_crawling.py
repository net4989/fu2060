import os
import time
import datetime
import sqlite3

from selenium import webdriver
from bs4 import BeautifulSoup






# txt 저장폴더
Folder_Name_TXT_Store = 'txt_store'
# db 저장폴더
Folder_Name_DB_Store = 'db_store'






# 선택종목 crawling
def txt_pickup_for_stock_crawling():
    # 폴더
    # Folder_Name_TXT_Store 폴더
    is_store_folder = os.path.isdir(Folder_Name_TXT_Store)
    if is_store_folder == False:
        return
    # 선택종목
    choice_stock_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store
    is_year_folder = os.path.isdir(choice_stock_files_path)
    if is_year_folder == False:
        return
    dir_list_files = os.listdir(choice_stock_files_path)
    # choice_stock_list 리스트 생성
    choice_stock_list = []
    choice_stock_filename = 'favorites_item_list'
    for f in dir_list_files:
        if f.startswith(choice_stock_filename):
            choice_stock_list.append(f)
    # print(choice_stock_list)
    # choice_stock 파일이 없으면 패스
    if len(choice_stock_list) == 0:
        return
    # 텍스트파일에서 종목데이타 저장하기
    crawling_item_data = {'stock_item_no': [], 'stock_item_percent': [], 'stock_item_name': [],
                          'stock_item_category': [], 'stock_item_buy_opinion': [], 'stock_item_buy_reason': []}
    for file_name in choice_stock_list:
        choice_stock_file_path_name = choice_stock_files_path + '/' + file_name
        f = open(choice_stock_file_path_name, 'rt', encoding='UTF8')
        choice_stock_items = f.readlines()
        f.close()
        for choice_stock_item in choice_stock_items:
            item = choice_stock_item.split('::')
            # print(item)
            crawling_item_data['stock_item_no'].append(item[0])
            crawling_item_data['stock_item_percent'].append(item[1])
            crawling_item_data['stock_item_name'].append(item[2])
            crawling_item_data['stock_item_category'].append(item[3])
            crawling_item_data['stock_item_buy_opinion'].append(item[4])
            crawling_item_data['stock_item_buy_reason'].append(item[5])
    print(crawling_item_data)

    # # naver_stock_info_fn 실행
    # naver_stock_info_fn(crawling_item_data)

    # # 온라인기업정보 웹크롤링
    # def naver_stock_info_fn(crawling_item_data):
    # 테이블명 구하기
    # db_store 폴더
    is_store_folder = os.path.isdir(Folder_Name_DB_Store)
    if is_store_folder == False:
        return
    dir_list_year = os.listdir(Folder_Name_DB_Store)
    # print(dir_list_year)
    # 폴더
    current_year = datetime.datetime.today().strftime("%Y")
    current_today = datetime.datetime.today().strftime("%Y%m%d")
    # print(current_year)
    db_file_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + current_year
    is_db_file = os.path.isdir(db_file_path)
    if is_db_file == False:
        return
    # db명 설정
    db_name_db = Folder_Name_DB_Store + '/' + current_year + '/' + 'favorites_crawling_data' + '.db'
    # print(db_name_db)

    # 테이블명 가져오기
    con = sqlite3.connect(db_name_db)
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    total_table_name_of_db = cursor.fetchall()
    print(total_table_name_of_db)

    # 실제 테이블 구하기
    total_table_name = []
    for table in total_table_name_of_db:
        total_table_name.append(table[0])
    print(total_table_name)

    ################################
    # 온라인기업정보
    ################################
    # 웹드라이브를 크롬브라우저 버젼과 맞게 동일 폴더에 넣어준다.
    # chrome://version

    # 크롬 브라우저 풀창으로 열기 옵션
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    webd = webdriver.Chrome(chrome_options=options)
    delay_browser = 3  # seconds - 에러발생 엘리먼트 대기시간

    # 새로운 텍스트 저장내용 딕셔너리 선언
    crawling_item_data_new = {'stock_item_no': [], 'stock_item_percent': [], 'stock_item_name': [],
                              'stock_item_category': [], 'stock_item_buy_opinion': [], 'stock_item_buy_reason': []}
    for i, crawling_item in enumerate(crawling_item_data['stock_item_no']):
        # 웹사이트 접속(링크주소 직접입력)
        naver_stock_info_url = (
                'https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd=%s' % (crawling_item)
        )
        # url에 접근
        webd.get(naver_stock_info_url)
        # 잠시쉬어감
        time.sleep(delay_browser)

        # 페이지의 elements모두 가져오기
        html = webd.page_source  # 페이지의 elements모두 가져오기
        soup = BeautifulSoup(html, 'html.parser')  # BeautifulSoup사용하기
        # CSS Selector를 통해 html요소들을 찾아낸다.
        # print(soup)

        print(crawling_item)
        print(crawling_item_data['stock_item_name'][i])
        # 요소 분석
        opinion_point_b = soup.select(
            '#cTB15 > tbody > tr > td > b'
        )
        opinion_point = soup.find_all(
            'td', 'noline-bottom line-right center cUp'
        )
        opinion_point_cnt = soup.find_all(
            'td', 'noline-bottom center'
        )
        print(opinion_point_b)
        # print(opinion_point)
        # print(opinion_point_cnt)

        opinion_point_b_list = []
        opinion_point_list = []
        opinion_point_cnt_list = []

        for b in opinion_point_b:
            opinion_point_b_list.append(b.get_text())
        if len(opinion_point_b_list) == 0:
            opinion_point_b_list.append('0.00')
        # 예외처리
        elif b.get_text() == '\xa0':
            opinion_point_b_list[0] = '0.00'
        print(opinion_point_b_list)

        # for p in opinion_point:
        #     opinion_point_list.append(p.get_text())
        # print(opinion_point_list)

        for c in opinion_point_cnt:
            opinion_point_cnt_list.append(c.get_text())
        if len(opinion_point_cnt_list) == 0:
            opinion_point_cnt_list.append('0')
        # 예외처리
        elif c.get_text() == '':
            opinion_point_cnt_list[0] = '0'
        print(opinion_point_cnt_list)





        # 요소 분석
        money_allocation = soup.find_all(
            'b', 'num'
        )
        print(money_allocation)





    #     # db테이블 존재여부에 따라
    #     if crawling_item in total_table_name:
    #
    #         # db읽기
    #         cursor.execute(
    #             "SELECT * FROM '%s'" % (crawling_item)
    #         )
    #         db_data = cursor.fetchall()
    #         for data in db_data:
    #             print(data)
    #
    #         # print(data)
    #         # 크롤링 투자의견 3.6이상 / 다섯보다 많음
    #         if (float(opinion_point_b_list[0]) > 3.6) and (int(opinion_point_cnt_list[0]) >= 5):
    #             print('투자의견 3.6이상 / 다섯보다 많음')
    #
    #             # 투자의견 상승중
    #             if float(opinion_point_b_list[0]) > float(data[4]):
    #                 print('상승중')
    #                 cursor.execute(
    #                     "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s, %s, '%s')" %
    #                     (crawling_item, current_today, crawling_item_data['stock_item_no'][i],
    #                      crawling_item_data['stock_item_name'][i], crawling_item_data['stock_item_category'][i],
    #                      opinion_point_b_list[0], opinion_point_cnt_list[0],
    #                      crawling_item_data['stock_item_buy_reason'][i])
    #                 )
    #                 crawling_item_data_new['stock_item_no'].append(crawling_item_data['stock_item_no'][i])
    #                 crawling_item_data_new['stock_item_percent'].append('05')
    #                 crawling_item_data_new['stock_item_name'].append(crawling_item_data['stock_item_name'][i])
    #                 crawling_item_data_new['stock_item_category'].append(
    #                     crawling_item_data['stock_item_category'][i])
    #                 crawling_item_data_new['stock_item_buy_opinion'].append(
    #                     opinion_point_b_list[0] + '/' + data[4] + '/' + '상승중' + '/' + opinion_point_cnt_list[0])
    #                 crawling_item_data_new['stock_item_buy_reason'].append(
    #                     crawling_item_data['stock_item_buy_reason'][i])
    #
    #             # 투자의견 하강중
    #             elif float(opinion_point_b_list[0]) < float(data[4]):
    #                 print('하강중')
    #                 cursor.execute(
    #                     "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s, %s, '%s')" %
    #                     (crawling_item, current_today, crawling_item_data['stock_item_no'][i],
    #                      crawling_item_data['stock_item_name'][i], crawling_item_data['stock_item_category'][i],
    #                      opinion_point_b_list[0], opinion_point_cnt_list[0],
    #                      crawling_item_data['stock_item_buy_reason'][i])
    #                 )
    #                 crawling_item_data_new['stock_item_no'].append(crawling_item_data['stock_item_no'][i])
    #                 crawling_item_data_new['stock_item_percent'].append('15')
    #                 crawling_item_data_new['stock_item_name'].append(crawling_item_data['stock_item_name'][i])
    #                 crawling_item_data_new['stock_item_category'].append(
    #                     crawling_item_data['stock_item_category'][i])
    #                 crawling_item_data_new['stock_item_buy_opinion'].append(
    #                     opinion_point_b_list[0] + '/' + data[4] + '/' + '하강중' + '/' + opinion_point_cnt_list[0])
    #                 crawling_item_data_new['stock_item_buy_reason'].append(
    #                     crawling_item_data['stock_item_buy_reason'][i])
    #
    #             # 투자의견 동일
    #             else:
    #                 print('동일')
    #                 crawling_item_data_new['stock_item_no'].append(crawling_item_data['stock_item_no'][i])
    #                 crawling_item_data_new['stock_item_percent'].append(crawling_item_data['stock_item_percent'][i])
    #                 crawling_item_data_new['stock_item_name'].append(crawling_item_data['stock_item_name'][i])
    #                 crawling_item_data_new['stock_item_category'].append(
    #                     crawling_item_data['stock_item_category'][i])
    #                 crawling_item_data_new['stock_item_buy_opinion'].append(
    #                     opinion_point_b_list[0] + '/' + data[4] + '/' + '동일' + '/' + opinion_point_cnt_list[0])
    #                 crawling_item_data_new['stock_item_buy_reason'].append(
    #                     crawling_item_data['stock_item_buy_reason'][i])
    #
    #         # 투자의견 건수 5건 이하 / 투자의견 3.6 이하
    #         else:
    #
    #             # 투자의견 상승중
    #             if float(opinion_point_b_list[0]) > float(data[4]):
    #                 print('상승중')
    #                 cursor.execute(
    #                     "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s, %s, '%s')" %
    #                     (crawling_item, current_today, crawling_item_data['stock_item_no'][i],
    #                      crawling_item_data['stock_item_name'][i], crawling_item_data['stock_item_category'][i],
    #                      opinion_point_b_list[0], opinion_point_cnt_list[0],
    #                      crawling_item_data['stock_item_buy_reason'][i])
    #                 )
    #                 crawling_item_data_new['stock_item_no'].append(crawling_item_data['stock_item_no'][i])
    #                 crawling_item_data_new['stock_item_percent'].append(crawling_item_data['stock_item_percent'][i])
    #                 crawling_item_data_new['stock_item_name'].append(crawling_item_data['stock_item_name'][i])
    #                 crawling_item_data_new['stock_item_category'].append(
    #                     crawling_item_data['stock_item_category'][i])
    #                 crawling_item_data_new['stock_item_buy_opinion'].append(
    #                     opinion_point_b_list[0] + '/' + data[4] + '/' + '상승중' + '/' + opinion_point_cnt_list[0])
    #                 crawling_item_data_new['stock_item_buy_reason'].append(
    #                     crawling_item_data['stock_item_buy_reason'][i])
    #
    #             # 투자의견 하강중
    #             elif float(opinion_point_b_list[0]) < float(data[4]):
    #                 print('하강중')
    #                 cursor.execute(
    #                     "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s, %s, '%s')" %
    #                     (crawling_item, current_today, crawling_item_data['stock_item_no'][i],
    #                      crawling_item_data['stock_item_name'][i], crawling_item_data['stock_item_category'][i],
    #                      opinion_point_b_list[0], opinion_point_cnt_list[0],
    #                      crawling_item_data['stock_item_buy_reason'][i])
    #                 )
    #                 crawling_item_data_new['stock_item_no'].append(crawling_item_data['stock_item_no'][i])
    #                 crawling_item_data_new['stock_item_percent'].append(crawling_item_data['stock_item_percent'][i])
    #                 crawling_item_data_new['stock_item_name'].append(crawling_item_data['stock_item_name'][i])
    #                 crawling_item_data_new['stock_item_category'].append(
    #                     crawling_item_data['stock_item_category'][i])
    #                 crawling_item_data_new['stock_item_buy_opinion'].append(
    #                     opinion_point_b_list[0] + '/' + data[4] + '/' + '하강중' + '/' + opinion_point_cnt_list[0])
    #                 crawling_item_data_new['stock_item_buy_reason'].append(
    #                     crawling_item_data['stock_item_buy_reason'][i])
    #
    #             # 투자의견 동일
    #             else:
    #                 print('동일')
    #
    #                 # 매수추천 건수가 5건 미만일때
    #                 crawling_item_data_new['stock_item_no'].append(crawling_item_data['stock_item_no'][i])
    #                 crawling_item_data_new['stock_item_percent'].append(crawling_item_data['stock_item_percent'][i])
    #                 crawling_item_data_new['stock_item_name'].append(crawling_item_data['stock_item_name'][i])
    #                 crawling_item_data_new['stock_item_category'].append(
    #                     crawling_item_data['stock_item_category'][i])
    #                 crawling_item_data_new['stock_item_buy_opinion'].append(
    #                     opinion_point_b_list[0] + '/' + data[4] + '/' + '동일' + '/' + opinion_point_cnt_list[0])
    #                 crawling_item_data_new['stock_item_buy_reason'].append(
    #                     crawling_item_data['stock_item_buy_reason'][i])
    #
    #     # 종목코드 db테이블 없으면 생성
    #     else:
    #         cursor.execute(
    #             "CREATE TABLE '%s'(date text, item_no text, item_name text, category text, buy_opinion text, buy_cnt text, buy_reason text)" % (
    #                 crawling_item)
    #         )
    #         cursor.execute(
    #             "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s, %s, '%s')" %
    #             (crawling_item, current_today, crawling_item_data['stock_item_no'][i],
    #              crawling_item_data['stock_item_name'][i], crawling_item_data['stock_item_category'][i],
    #              opinion_point_b_list[0], opinion_point_cnt_list[0], crawling_item_data['stock_item_buy_reason'][i])
    #         )
    #         crawling_item_data_new['stock_item_no'].append(crawling_item_data['stock_item_no'][i])
    #         crawling_item_data_new['stock_item_percent'].append(crawling_item_data['stock_item_percent'][i])
    #         crawling_item_data_new['stock_item_name'].append(crawling_item_data['stock_item_name'][i])
    #         crawling_item_data_new['stock_item_category'].append(crawling_item_data['stock_item_category'][i])
    #         crawling_item_data_new['stock_item_buy_opinion'].append(
    #             opinion_point_b_list[0] + '/' + opinion_point_cnt_list[0])
    #         crawling_item_data_new['stock_item_buy_reason'].append(crawling_item_data['stock_item_buy_reason'][i])
    #
    # # db닫기
    # con.commit()
    # con.close()
    #
    # # 크롬 종료
    # webd.close()

    # # 최종 텍스트 출력
    # print(crawling_item_data_new)
    # # crawling_item_data_new
    # f = open(choice_stock_files_path + '/' + choice_stock_filename + '.txt', 'wt', encoding='UTF8')
    # for i in range(len(crawling_item_data_new['stock_item_no'])):
    #     stock_item_no = crawling_item_data_new['stock_item_no'][i]
    #     stock_item_percent = crawling_item_data_new['stock_item_percent'][i]
    #     stock_item_name = crawling_item_data_new['stock_item_name'][i]
    #     stock_item_category = crawling_item_data_new['stock_item_category'][i]
    #     stock_item_buy_opinion = crawling_item_data_new['stock_item_buy_opinion'][i]
    #     stock_item_buy_reason = crawling_item_data_new['stock_item_buy_reason'][i]
    #     store_data = stock_item_no + '::' + stock_item_percent + '::' + stock_item_name + '::' + stock_item_category + '::' + stock_item_buy_opinion + '::' + stock_item_buy_reason
    #     f.write(store_data)
    # f.close()


if __name__ == '__main__':
    print(__name__)

    # 선택종목 전체종목 txt 호출
    txt_pickup_for_stock_crawling()






