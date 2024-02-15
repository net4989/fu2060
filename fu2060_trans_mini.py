import time
import math
import datetime
from PyQt5 import uic
import shutil

# 데이타 저장관련
import pandas as pd
import sqlite3
# 차트그리기
import matplotlib.pyplot as plt
# matplotlib를 이용해 PyQt 내에 그래프를 그리려면 FigureCanvasQTAgg 클래스를 사용
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from selenium import webdriver
from bs4 import BeautifulSoup

# 자체모듈
from Api_server_rq import *
from Cross_check import *
from Delta_check import *
from Step_Runprice_Delta_check import *
from Layout_ui_chart import *
from Data_store_pickup import *
from db_back_test import *
from Insu_check import *

from stock_trend_line_module import *



TR_REQ_TIME_INTERVAL = 0.2

# db 저장폴더
Folder_Name_DB_Store = 'db_store'
# txt 저장폴더
Folder_Name_TXT_Store = 'txt_store'
Global_Option_Item_Code = 'K200'

# 1회 최대 매수 건수
Buy_Item_Max_Cnt = 5
# 1회 1종목 진입가격
Market_In_Percent = 10
# 옵션 1회 진입가격
# 당일 매수 매도 종목 텍스트 저장 호출
File_Kind_Buy = 'buyed'
File_Kind_Sell = 'selled'

# 선물옵션 배수 머니
Option_Mul_Money = 250000
# 기조자산 범위
Basic_Property_Range = 2.5
# 중심가 기준 위아래 몇칸을 뒤질까요?
Up_CenterOption_Down = 9
# 중심가 기준 위아래 모니터 건수
Up2_CenterOption_Down2 = 2

# 그래프 세로 칸수
Chart_Ylim = 12

# 연결선물
Chain_Future_s_Item_Code = ['10100000']

# 선물 레버리지(10 or 20) 결정(*** 향후 투자금액이 커지면 ~20으로 변경 예정)
# :: 1 ~ 2 계약 바스켓 정도는 추가증거금 감당가능 판단 :: 20220316)
# 202209~ 옵션 매도 헷지방식으로 변경하면서 자산배정 변경(선물 3 바스켓, 매도헷지 : 델타 맞추기)
Future_s_Leverage_Int = 12



# Layout_ui_chart Layout 클래스 상속
class MyWindow(Layout):
    def __init__(self):
        # super().__init__()을 호출하는데 이는 부모 클래스에 정의된 __init__()을 호출하는 것을 의미합니다.
        # 이 예제에서는 MyWindow 클래스가 QMainWindow 클래스를 상속받았으므로 QMainWindow 클래스의 생성자인 __init__()을 호출
        super().__init__()

        # form_class를 상속받았기 때문에 form_class에 정의돼 있던 속성이나 메서드를 모두 상속받게 됩니다.
        # 따라서 다음과 같이 setupUi 메서드를 호출함으로써 Qt Designer를 통해 구성한 UI를 화면에 출력할 수 있습니다.
        # 참고로 setupUi라는 메서드 이름은 정해진 이름이기 때문에 그대로 사용
        # 버튼 객체에 대한 생성 및 바인딩은 setupUi 메서드에서 수행
        # Layout_ui_chart Layout 클래스 상속
        self.setupUi(self)
        # 메인윈도창 레이아웃 셋팅(차트)
        self.layout_chart_draw()
        self.setWindowTitle('fu2060_trans_mini(선물 트레이딩 & 옵션 매도 헷지)')

        # API_server
        self.kiwoom = Kiwoom()
        self._set_signal_slots()
        self.kiwoom.comm_connect()

        # 로그인 정보 가져오기
        self.accouns_id = self.kiwoom.get_login_info("USER_ID")
        self.accounts_name = self.kiwoom.get_login_info("USER_NAME")
        accouns_num = int(self.kiwoom.get_login_info("ACCOUNT_CNT"))
        accounts = self.kiwoom.get_login_info("ACCNO")

        # 계좌번호 셋팅
        accounts_list = accounts.split(';')[0:accouns_num]
        self.comboBox_acc.addItems(accounts_list)
        self.comboBox_acc_stock.addItems(accounts_list)

        # # 선정 종목 리스트는 PyTrader 프로그램이 시작되자마자 출력돼야 하므로 MyWindow 클래스의 생성자에서 load_buy_sell_list를 호출
        # self.load_buy_sell_list()

        # # 당월물(0), 순서대로(1~10)
        # #  = self.kiwoom.get_month_mall(5)
        # print(self.kiwoom.get_month_mall(0))
        # print(self.kiwoom.get_month_mall(1))
        # print(self.kiwoom.get_month_mall(2))
        # print(self.kiwoom.get_month_mall(3))

        # 1초에 한번씩 클럭 발생
        self.timer1 = QTimer(self)
        # self.timer1.start(Future_s_Leverage_Int * 100)
        self.timer1.timeout.connect(self.timer1sec)

        # 1초에 한번씩 클럭 발생(주문 체결 완료 결과)
        self.timer_order = QTimer(self)
        # self.timer_order.start(1000)
        self.timer_order.timeout.connect(self.timer_order_fn)

        # 1초에 한번씩 클럭 발생(주문 체결 완료 결과) stock
        self.timer_order_stock = QTimer(self)
        # self.timer_order_stock.start(1000)
        self.timer_order_stock.timeout.connect(self.timer_order_fn_stock)

        # 1분에 한번씩 클럭 발생
        self.timer60 = QTimer(self)
        # self.timer60.start(1000 * 60)
        self.timer60.timeout.connect(self.timer1min)

        # 1분에 한번씩 클럭 발생 :: 중심가 없을때
        self.timer_empty = QTimer(self)
        self.timer_empty.timeout.connect(self.timer_empty_fn)

        # textChanged는 사용자의 입력으로 텍스트가 변경되면 발생
        # lineEdit 객체가 변경될 때 호출되는 슬롯
        # # returnPressed는 사용자가 텍스트를 입력한 후 QLineEdit 객체에서 엔터키를눌렀을때 발생
        # self.lineEdit.textChanged.connect(self.code_changed)

        # 버튼의 이름을 확인한 후 해당 버튼에 대한 시그널과 슬롯을 연결

        # MyWindow 클래스의 생성자에 시그널과 슬롯을 연결하는 코드를 추가
        # currentIndexChanged 이벤트 핸들러
        # 가져오기 함수
        self.pushButton_datapickup_future_s_M.clicked.connect(self.data_pickup_future_s_chain_month_select_fill)
        self.comboBox_future_s_chain_month.activated.connect(self.data_pickup_future_s_chain_month)
        # 일봉 일자 불러오기
        self.pushButton_datapickup_code_s_D.clicked.connect(self.data_pickup_code_s_day_select_fill)
        self.comboBox_date_s_day.activated.connect(self.data_pickup_chart_s_day)
        # 일봉 코드 불러오기
        # [당일제외] 체크박스 무조건 켜놓기
        self.comboBox_code_s_day.activated.connect(self.data_pickup_chart_s_day)
        self.checkbox_today_x.setChecked(True)
        # checkbox_today_x 상태가 변할 때 마다 checkbox_today_x_statechanged 실행
        self.checkbox_today_x.stateChanged.connect(self.checkbox_today_x_statechanged)
        # QRadioButton
        self.radioButton_20.clicked.connect(self.radioButton_20_fn)
        self.radioButton_60.clicked.connect(self.radioButton_60_fn)
        self.radioButton_30.clicked.connect(self.radioButton_30_fn)
        self.radioButton_40.clicked.connect(self.radioButton_40_fn)
        # 그려질 차트의 일봉 갯수 초기화
        self.stock_price_candle_cnt = 0

        # 가져오기 함수
        self.pushButton_datapickup.clicked.connect(self.data_pickup_ready)

        # 선옵 잔고확인 클릭
        self.pushButton_myhave.clicked.connect(self.myhave_option_rq)
        # 계좌선택 이후 잔고확인 클릭 가능
        self.pushButton_myhave.setEnabled(False)
        # 자동주문 클릭
        self.pushButton_auto_order.clicked.connect(self.auto_order_button)
        # 계좌선택 이후 자동주문 클릭 가능
        self.pushButton_auto_order.setEnabled(False)

        # 장시작 / 장마감 (수동으로)
        # 장시작 3
        self.pushButton_market_start_3.clicked.connect(self.market_start_3)
        self.pushButton_market_start_3.setEnabled(True)
        # 장마감 c
        self.pushButton_market_ending_c.clicked.connect(self.market_ending_c)
        self.pushButton_market_ending_c.setEnabled(True)

        # 주문 테스트
        self.pushButton_3.clicked.connect(self.test)

        # 진입/청산 표시
        # 클릭 불가능
        self.pushButton_fu_buy_have.setEnabled(False)
        self.pushButton_fu_sell_have.setEnabled(False)
        self.pushButton_callhave.setEnabled(False)
        self.pushButton_puthave.setEnabled(False)

        # 콤보박스 리스트 차트
        # currentIndexChanged 이벤트 핸들러
        self.comboBox_year.activated.connect(self.select_monthmall)
        # currentIndexChanged 이벤트 핸들러
        self.comboBox_monthmall.activated.connect(self.select_date)
        # currentIndexChanged 이벤트 핸들러
        self.comboBox_date.activated.connect(self.select_time)
        # currentIndexChanged 이벤트 핸들러
        self.comboBox_time.activated.connect(self.listed_slot)

        # 변수선언
        # 선물 변화
        self.future_s_change_listed_var = []
        self.future_s_run = []

        self.real_time_total_cnt = 0
        self.real_time_count_for_1sec_max = 0
        self.real_time_total_cnt_accumul = []
        self.slow_cross_check_var = {'up2': [0], 'up1': [0], 'zero': [0], 'dn1': [0], 'dn2': [0],
                                'up2_c_d': [0], 'up1_c_d': [0], 'dn1_c_d': [0], 'dn2_c_d': [0],
                                'up2_p_d': [0], 'up1_p_d': [0], 'dn1_p_d': [0], 'dn2_p_d': [0]}

        # 자동주문
        self.auto_order_button_var = False
        # 선옵 잔고확인 버튼 변수
        self.myhave_option_button_var = False
        # 실시간 이벤트 처리 가능여부 변수
        self.receive_real_data_is_OK = False
        # [실시간 조회] 체크박스 무조건 켜놓기
        self.checkbox_realtime.setChecked(True)
        # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        self.MarketEndingVar = '0'
        # 선물변화 퍼센트(1.001 / 0.999 - 0.1% , 1.0008 / 0.9992 - 0.1%의 80%, 1.0005 / 0.9995 - 0.1%의 50%)
        self.future_s_percent_high = 1.002
        self.future_s_percent_low = 0.998
        # 옵션 다항회귀 분봉(0.1% => 0.2%)로 변경후 테스트(2021년 12월 22일~)

        # 시분초 : db 중복 시분 제외 변수선언
        self.db_overlap_time_list = []
        # 시분초 : db 중복 시분 제외 변수
        current_time = QTime.currentTime()
        db_overlap_time_except = current_time.toString('hh:mm')
        self.db_overlap_time_list.append(db_overlap_time_except)

        # 종목코드 앞자리
        self.Global_Option_Item_Code_var = 'K200_k200_s'
        # 기초자산 선택
        self.basic_choice = 'future_s'

        # -----
        # 영업일 기준 잔존일(부팅시 우선 공백처리)
        self.day_residue_str = ''
        self.printt('self.day_residue_str - 부팅시')
        self.printt(self.day_residue_str)
        # -----

        # 자료요청전 또는 장시작 전에 실시간신호 에러 방지를 위하여 부팅시 변수선언 먼저함
        # 인스턴스 변수 선언
        self.futrue_s_reset_output()
        # 인스턴스 변수 선언
        self.option_reset_output()
        # 인스턴스 변수 선언
        self.stock_have_data_reset_output()
        # 인스턴스 변수 선언
        self.option_s_sell_deposit_money_output()

        # 주문 실행 결과
        # 인스턴스 변수 선언
        self.reset_order_var()
        # 주문 실행 결과
        # 인스턴스 변수 선언
        self.reset_order_var_stock()

        # 인스턴스 변수 선언
        # 선옵잔고요청 변수선언
        # 주문시 선옵잔고 변수 초기화
        self.reset_myhave_var()

        # 콜/풋 월별시세요청
        self.call_put_data_rq()
        # 선물전체시세요청
        self.futrue_s_data_rq()

        # 서버구분(모의서버 : '1' /실서버 : '')
        if self.get_server_gubun() == '':
            # 옵션매도주문증거금 요청
            self.option_s_sell_deposit_money_data_rq()

        # 장마감 c_to_cf_hand
        self.c_to_cf_hand()
        # 장마감 c 이후 <= 20240123 이후 부터 장시작시와 마감시에 2회 실행하기로 함
        # 장시작시는 trend_line 과 시뮬레이션 저장 않함
        # 선물 및 즐겨찾기 주식 시세요청 용도만(20240205)

        # 롤오버 변수 False :: 선물 롤오버 함수 입장 가능
        self.future_s_roll_over_run_var = False

        # 당일날 재부팅이면 self.future_s_change 선물 현재값 넣어주고 가기
        self.data_pickup_today_rebooting()

        # 선물변화 프로세스 실행중 여부
        self.future_s_change_running = False

    # 부팅 바로 이후 중심가 변경시 self.selled_today_items 변수 선언이전 발생되는 에러 수정(20221123)
        # 당일 매도 종목 찾기
        self.selled_today_items = self.selled_today_items_search_fn()
        self.printt('# 당일 매도 종목 찾기')
        self.printt(self.selled_today_items)
        # 당일 매수 종목 찾기
        self.buyed_today_items = self.buyed_today_items_search_fn()
        self.printt('# 당일 매수 종목 찾기')
        self.printt(self.buyed_today_items)
    # 부팅 바로 이후 중심가 변경시 self.selled_today_items 변수 선언이전 발생되는 에러 수정(20221123)

        # 초단위 주문변수 초기화
        self.item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': [], 'state': [], 'order_no': []}
        # state : 0(선택), 1(주문), 2(취소), 3(체결-삭제)

        # 방금전 "체결"이 매도 혹은 매수 체크하여
        # 매도 였으면 매수먼저
        # 최초 부팅시에 self.last_order_sell_or_buy 는 1로 처리
        self.last_order_sell_or_buy = 1
        # 1건씩 주문
        self.order_cnt_onetime = 1

        # 선물 주문중인지 판단 변수(주문변수에 당월물 차월물 종목코드 있으면~~)
        # self.future_s_ordering = True 일경우에는 옵션관련 선물관련 함수 미 실행
        self.future_s_ordering = False

        # -----
        # 부팅시 => 1초 타이머 시작
        self.timer1.start(Future_s_Leverage_Int * 100)
        self.printt('부팅시 => 1초 타이머 시작')
        # -----

    # 이벤트 처리 슬롯
    def _set_signal_slots(self):
        self.kiwoom.OnEventConnect.connect(self.kiwoom._event_connect)              # 로그인 이벤트
        self.kiwoom.OnReceiveTrData.connect(self._receive_tr_data)                  # 서버요청 이벤트
        self.kiwoom.OnReceiveRealData.connect(self._receive_real_data)              # 실시간 이벤트
        self.kiwoom.OnReceiveChejanData.connect(self._receive_chejan_data)          # 주문체결 시점에서 키움증권 서버가 발생

    # 조회수신한 멀티데이터의 갯수(반복)수
    def _get_repeat_cnt(self, trcode, rqname):
        ret = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret

    # OnReceiveTRData()이벤트가 호출될때 조회데이터를 얻어오는 함수
    def _comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.kiwoom.dynamicCall("CommGetData(QString, QString, QString, int, QString", code,
                               real_type, field_name, index, item_name)
        return ret.strip()

    # 서버구분(모의서버 : '1')
    # 실 서버에서 수익률은 소수점 표시 없이 전달되지만 모의투자에서는 소수점을 포함해서 데이터가 전달됩니다.
    # 따라서 접속 서버를 구분해서 데이터를 다르게 처리할 필요
    def get_server_gubun(self):
        ret = self.kiwoom.dynamicCall("KOA_Functions(QString, QString)", "GetServerGubun", "")
        return ret

    # 데이타 요청/처리/실시간
    # 입력데이터 서버전송(선물전체시세요청)
    def server_set_rq_future_s_data(self, sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID, sValue)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(콜/풋 월별시세요청)
    def server_set_rq_call_put_data(self, sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID, sValue)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)
    # 입력데이터 서버전송(옵션매도주문증거금)
    def server_set_rq_option_s_sell_deposit_money_data(self, sID1, sValue1, sID2, sValue2, sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.set_input_value(sID2, sValue2)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(opt50072 : 선물월차트요청)
    def server_set_rq_future_s_shlc_month_data(self, sID1, sValue1, sID2, sValue2, sRQName,
                                                 sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.set_input_value(sID2, sValue2)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(OPT50030 : 선물일차트요청)
    def server_set_rq_future_s_shlc_day_data(self, sID1, sValue1, sRQName,
                                                 sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(opt10083 : 주식월봉차트조회요청)
    def server_set_rq_stock_shlc_month_data(self, sID1, sValue1, sID2, sValue2, sID3, sValue3, sID4, sValue4, sRQName,
                                            sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.set_input_value(sID2, sValue2)
        self.set_input_value(sID3, sValue3)
        self.set_input_value(sID4, sValue4)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(opt10081 : 주식일봉차트조회요청)
    def server_set_rq_stock_shlc_data(self, sID1, sValue1, sID2, sValue2, sID3, sValue3, sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.set_input_value(sID2, sValue2)
        self.set_input_value(sID3, sValue3)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(업종별주가요청)
    def server_set_rq_stock_price(self, sID1, sValue1, sID2, sValue2, sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.set_input_value(sID2, sValue2)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 계좌평가잔고내역요청[stock]
    def server_set_rq_stock_have_data(self, sID1, sValue1, sID2, sValue2, sID3, sValue3, sID4, sValue4, sRQName,
                                      sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.set_input_value(sID2, sValue2)
        self.set_input_value(sID3, sValue3)
        self.set_input_value(sID4, sValue4)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(선옵잔존일조회요청)
    def server_set_rq_DayResidue(self, sID1, sValue1, sID2, sValue2, sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.set_input_value(sID2, sValue2)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(선옵잔고요청)
    def server_set_rq_MyHave(self, sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID, sValue)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(예탁금및증거금조회)
    def server_set_rq_OptionMoney(self, sID1, sValue1, sID2, sValue2, sID3, sValue3, sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, sValue1)
        self.set_input_value(sID2, sValue2)
        self.set_input_value(sID3, sValue3)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

    # 입력데이터 서버전송(선옵계좌별주문가능수량요청)
    def server_set_rq_future_s_option_s_order_able_cnt(self, sID1, accountrunVar, sID2, sValue2, sID3, sValue3,
                                                            sID4, sValue4, sID5, sValue5, sID6, sValue6, sID7, sValue7,
                                                            sRQName, sTrCode, nPrevNext, sScreenNo):
        self.set_input_value(sID1, accountrunVar)
        self.set_input_value(sID2, sValue2)
        self.set_input_value(sID3, sValue3)
        self.set_input_value(sID4, sValue4)
        self.set_input_value(sID5, sValue5)
        self.set_input_value(sID6, sValue6)
        self.set_input_value(sID7, sValue7)
        self.comm_rq_data(sRQName, sTrCode, nPrevNext, sScreenNo)

# 데이타 요청/처리/실시간
    # 서버전송값 입력
    def set_input_value(self, sID, sValue):
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", sID, sValue)

    # 서버전송
    def comm_rq_data(self, sRQName, sTrCode, nPrevNext, sScreenNo):
        time.sleep(TR_REQ_TIME_INTERVAL)
        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", sRQName, sTrCode, nPrevNext, sScreenNo)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    # 서버전송
    def comm_kw_rq_data(self, sArrCode, bNext, nCodeCount, nTypeFlag, sRQName, sScreenNo):
        time.sleep(TR_REQ_TIME_INTERVAL)
        self.kiwoom.dynamicCall("CommKwRqData(QString, QBoolean, int, int, QString, QString)", sArrCode, bNext, nCodeCount, nTypeFlag, sRQName, sScreenNo)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

# 데이타 요청/처리/실시간
    # 서버 이벤트 발생후 처리
    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        if next == '2':
            self.remained_data = True

            # -----
            self.printt('# 연속조회 값이 있는지 확인[self.remained_data]')
            self.printt(self.remained_data)
            # -----

        else:
            self.remained_data = False

        # -----
        if rqname == "선물전체시세요청":
            self._OPTFOFID(rqname, trcode)
        elif rqname == "선물전체시세요청_45":
            self._OPTFOFID_45(rqname, trcode)
        elif rqname == "선물월차트요청":
            self._opt50072(rqname, trcode)
        elif rqname == "선물일차트요청":
            self._OPT50030(rqname, trcode)

        elif rqname == "콜종목결제월별시세요청":
            self._opt50021(rqname, trcode)
        elif rqname == "풋종목결제월별시세요청":
            self._opt50022(rqname, trcode)

        elif rqname == "콜종목결제월별시세요청_45":
            self._opt50021_45(rqname, trcode)
        elif rqname == "풋종목결제월별시세요청_45":
            self._opt50022_45(rqname, trcode)

        elif rqname == "옵션매도주문증거금":
            self._opw20015(rqname, trcode)

        elif rqname == "업종별주가요청":
            self._opt20002(rqname, trcode)
        elif rqname == "계좌평가잔고내역요청":
            self._opw00018(rqname, trcode)

        elif rqname == "선옵잔존일조회요청":
            self._opt50033(rqname, trcode)
        elif rqname == "선옵잔고요청":
            self._opt50027(rqname, trcode)
        elif rqname == "예탁금및증거금조회":
            self._opw20010(rqname, trcode)
        elif rqname == "선옵계좌별주문가능수량요청":
            self._opw20009(rqname, trcode)

        elif rqname == "체결강도조회":
            self._optkwfid(rqname, trcode)

        elif rqname == "주식월봉차트조회요청":
            self._opt10083(rqname, trcode)

        elif rqname == "주식일봉차트조회요청":
            self._opt10081(rqname, trcode)
        # -----

        try:
            self.tr_event_loop.exit()
        except AttributeError:
            pass

# 서버 수신 데이타 처리

    # _OPTFOFID(선물전체시세요청)
    def _OPTFOFID(self, rqname, trcode):
        # self.option_price_rows = self._get_repeat_cnt(trcode, rqname)
        # 싱글데이터
        item_code = self._comm_get_data(trcode, "", rqname, 0, "종목코드")
        item_name = self._comm_get_data(trcode, "", rqname, 0, "종목명")
        run_price = self._comm_get_data(trcode, "", rqname, 0, "현재가")
        sell_price = self._comm_get_data(trcode, "", rqname, 0, "매도호가1")
        buy_price = self._comm_get_data(trcode, "", rqname, 0, "매수호가1")
        vol_cnt = self._comm_get_data(trcode, "", rqname, 0, "거래량")
        start_price = self._comm_get_data(trcode, "", rqname, 0, "시가")
        high_price = self._comm_get_data(trcode, "", rqname, 0, "고가")
        low_price = self._comm_get_data(trcode, "", rqname, 0, "저가")
        theorist_price = self._comm_get_data(trcode, "", rqname, 0, "이론가")
        market_basis = self._comm_get_data(trcode, "", rqname, 0, "시장베이시스")
        theorist_basis = self._comm_get_data(trcode, "", rqname, 0, "이론베이시스")
        kospi_trans = self._comm_get_data(trcode, "", rqname, 0, "지수환산")
        day_residue = self._comm_get_data(trcode, "", rqname, 0, "영업일기준잔존일")

        self.futrue_s_data['item_code'].append(str(item_code))
        self.futrue_s_data['item_name'].append(str(item_name))
        self.futrue_s_data['run_price'].append(abs(float(run_price)))
        self.futrue_s_data['sell_price'].append(abs(float(sell_price)))
        self.futrue_s_data['buy_price'].append(abs(float(buy_price)))
        self.futrue_s_data['vol_cnt'].append(abs(int(vol_cnt)))
        self.futrue_s_data['start_price'].append(abs(float(start_price)))
        self.futrue_s_data['high_price'].append(abs(float(high_price)))
        self.futrue_s_data['low_price'].append(abs(float(low_price)))
        self.futrue_s_data['theorist_price'].append(abs(float(theorist_price)))
        self.futrue_s_data['market_basis'].append(abs(float(market_basis)))
        self.futrue_s_data['theorist_basis'].append(abs(float(theorist_basis)))
        self.futrue_s_data['kospi_trans'].append(abs(float(kospi_trans)))
        self.futrue_s_data['day_residue'].append(abs(int(day_residue)))

    # _OPTFOFID_45(선물전체시세요청_차월물)
    def _OPTFOFID_45(self, rqname, trcode):
        # self.option_price_rows = self._get_repeat_cnt(trcode, rqname)
        # 싱글데이터
        item_code = self._comm_get_data(trcode, "", rqname, 0, "종목코드")
        item_name = self._comm_get_data(trcode, "", rqname, 0, "종목명")
        run_price = self._comm_get_data(trcode, "", rqname, 0, "현재가")
        sell_price = self._comm_get_data(trcode, "", rqname, 0, "매도호가1")
        buy_price = self._comm_get_data(trcode, "", rqname, 0, "매수호가1")
        vol_cnt = self._comm_get_data(trcode, "", rqname, 0, "거래량")
        start_price = self._comm_get_data(trcode, "", rqname, 0, "시가")
        high_price = self._comm_get_data(trcode, "", rqname, 0, "고가")
        low_price = self._comm_get_data(trcode, "", rqname, 0, "저가")
        theorist_price = self._comm_get_data(trcode, "", rqname, 0, "이론가")
        market_basis = self._comm_get_data(trcode, "", rqname, 0, "시장베이시스")
        theorist_basis = self._comm_get_data(trcode, "", rqname, 0, "이론베이시스")
        kospi_trans = self._comm_get_data(trcode, "", rqname, 0, "지수환산")
        day_residue = self._comm_get_data(trcode, "", rqname, 0, "영업일기준잔존일")

        self.futrue_s_data_45['item_code'].append(str(item_code))
        self.futrue_s_data_45['item_name'].append(str(item_name))
        self.futrue_s_data_45['run_price'].append(abs(float(run_price)))
        self.futrue_s_data_45['sell_price'].append(abs(float(sell_price)))
        self.futrue_s_data_45['buy_price'].append(abs(float(buy_price)))
        self.futrue_s_data_45['vol_cnt'].append(abs(int(vol_cnt)))
        self.futrue_s_data_45['start_price'].append(abs(float(start_price)))
        self.futrue_s_data_45['high_price'].append(abs(float(high_price)))
        self.futrue_s_data_45['low_price'].append(abs(float(low_price)))
        self.futrue_s_data_45['theorist_price'].append(abs(float(theorist_price)))
        self.futrue_s_data_45['market_basis'].append(abs(float(market_basis)))
        self.futrue_s_data_45['theorist_basis'].append(abs(float(theorist_basis)))
        self.futrue_s_data_45['kospi_trans'].append(abs(float(kospi_trans)))
        self.futrue_s_data_45['day_residue'].append(abs(int(day_residue)))

    # _opt50021(콜(최근)종목결제월별시세요청)
    def _opt50021(self, rqname, trcode):
        self.option_price_rows = self._get_repeat_cnt(trcode, rqname)
        # multi data
        for i in range(self.option_price_rows):
            code = self._comm_get_data(trcode, "", rqname, i, "종목코드")
            option_price = self._comm_get_data(trcode, "", rqname, i, "행사가")
            run_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            sell_price = self._comm_get_data(trcode, "", rqname, i, "매도호가")
            sell_cnt = self._comm_get_data(trcode, "", rqname, i, "매도호가수량")
            buy_price = self._comm_get_data(trcode, "", rqname, i, "매수호가")
            buy_cnt = self._comm_get_data(trcode, "", rqname, i, "매수호가수량")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "누적거래량")

            Delta = self._comm_get_data(trcode, "", rqname, i, "델타")
            Gamma = self._comm_get_data(trcode, "", rqname, i, "감마")
            Theta = self._comm_get_data(trcode, "", rqname, i, "세타")
            Vega = self._comm_get_data(trcode, "", rqname, i, "베가")
            Rho = self._comm_get_data(trcode, "", rqname, i, "로")

            # 최상단과 최하단의 매수도호가는 공백임
            if (sell_price == '') or (buy_price == ''):
                sell_price = 0
                buy_price = 0

            self.output_call_option_data['code'].append(str(code))
            self.output_call_option_data['option_price'].append(str(option_price))
            self.output_call_option_data['run_price'].append(abs(float(run_price)))
            self.output_call_option_data['sell_price'].append(abs(float(sell_price)))
            self.output_call_option_data['sell_cnt'].append(abs(int(sell_cnt)))
            self.output_call_option_data['buy_price'].append(abs(float(buy_price)))
            self.output_call_option_data['buy_cnt'].append(abs(int(buy_cnt)))
            self.output_call_option_data['vol_cnt'].append(abs(int(vol_cnt)))

            self.output_call_option_data['Delta'].append(abs(float(Delta)))
            self.output_call_option_data['Gamma'].append(abs(float(Gamma)))
            self.output_call_option_data['Theta'].append(abs(float(Theta)))
            self.output_call_option_data['Vega'].append(abs(float(Vega)))
            self.output_call_option_data['Rho'].append(abs(float(Rho)))

            # (콜(최근)종목결제월별시세요청)::선물시세와 코스피200시세 강제로 0 바인딩
            self.output_call_option_data['future_s'].append(abs(float(0)))
            self.output_call_option_data['k200_s'].append(abs(float(0)))
            # (콜(최근)종목결제월별시세요청)::체결강도조회 강제로 0 바인딩
            self.output_call_option_data['deal_power'].append(abs(float(0)))

    # _opt50022(풋(최근)종목결제월별시세요청)
    def _opt50022(self, rqname, trcode):
        # multi data
        for i in range(self.option_price_rows):
            code = self._comm_get_data(trcode, "", rqname, i, "종목코드")
            option_price = self._comm_get_data(trcode, "", rqname, i, "행사가")
            run_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            sell_price = self._comm_get_data(trcode, "", rqname, i, "매도호가")
            sell_cnt = self._comm_get_data(trcode, "", rqname, i, "매도호가수량")
            buy_price = self._comm_get_data(trcode, "", rqname, i, "매수호가")
            buy_cnt = self._comm_get_data(trcode, "", rqname, i, "매수호가수량")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "누적거래량")

            Delta = self._comm_get_data(trcode, "", rqname, i, "델타")
            Gamma = self._comm_get_data(trcode, "", rqname, i, "감마")
            Theta = self._comm_get_data(trcode, "", rqname, i, "세타")
            Vega = self._comm_get_data(trcode, "", rqname, i, "베가")
            Rho = self._comm_get_data(trcode, "", rqname, i, "로")

            # 최상단과 최하단의 매수도호가는 공백임
            if (sell_price == '') or (buy_price == ''):
                sell_price = 0
                buy_price = 0

            self.output_put_option_data['code'].append(str(code))
            self.output_put_option_data['option_price'].append(str(option_price))
            self.output_put_option_data['run_price'].append(abs(float(run_price)))
            self.output_put_option_data['sell_price'].append(abs(float(sell_price)))
            self.output_put_option_data['sell_cnt'].append(abs(int(sell_cnt)))
            self.output_put_option_data['buy_price'].append(abs(float(buy_price)))
            self.output_put_option_data['buy_cnt'].append(abs(int(buy_cnt)))
            self.output_put_option_data['vol_cnt'].append(abs(int(vol_cnt)))

            self.output_put_option_data['Delta'].append(abs(float(Delta)))
            self.output_put_option_data['Gamma'].append(abs(float(Gamma)))
            self.output_put_option_data['Theta'].append(abs(float(Theta)))
            self.output_put_option_data['Vega'].append(abs(float(Vega)))
            self.output_put_option_data['Rho'].append(abs(float(Rho)))

            # (풋(최근)종목결제월별시세요청)::선물시세와 코스피200시세 강제로 0 바인딩
            self.output_put_option_data['future_s'].append(abs(float(0)))
            self.output_put_option_data['k200_s'].append(abs(float(0)))
            # (풋(최근)종목결제월별시세요청)::체결강도조회 강제로 0 바인딩
            self.output_put_option_data['deal_power'].append(abs(float(0)))

    # _opt50021_45(콜종목결제월별시세요청_45)
    def _opt50021_45(self, rqname, trcode):
        self.option_price_rows_45 = self._get_repeat_cnt(trcode, rqname)
        # multi data
        for i in range(self.option_price_rows_45):
            code = self._comm_get_data(trcode, "", rqname, i, "종목코드")
            option_price = self._comm_get_data(trcode, "", rqname, i, "행사가")
            run_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            sell_price = self._comm_get_data(trcode, "", rqname, i, "매도호가")
            sell_cnt = self._comm_get_data(trcode, "", rqname, i, "매도호가수량")
            buy_price = self._comm_get_data(trcode, "", rqname, i, "매수호가")
            buy_cnt = self._comm_get_data(trcode, "", rqname, i, "매수호가수량")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "누적거래량")

            Delta = self._comm_get_data(trcode, "", rqname, i, "델타")
            Gamma = self._comm_get_data(trcode, "", rqname, i, "감마")
            Theta = self._comm_get_data(trcode, "", rqname, i, "세타")
            Vega = self._comm_get_data(trcode, "", rqname, i, "베가")
            Rho = self._comm_get_data(trcode, "", rqname, i, "로")

            # 최상단과 최하단의 매수도호가는 공백임
            if (sell_price == '') or (buy_price == ''):
                sell_price = 0
                buy_price = 0

            self.output_call_option_data_45['code'].append(str(code))
            self.output_call_option_data_45['option_price'].append(str(option_price))
            self.output_call_option_data_45['run_price'].append(abs(float(run_price)))
            self.output_call_option_data_45['sell_price'].append(abs(float(sell_price)))
            self.output_call_option_data_45['sell_cnt'].append(abs(int(sell_cnt)))
            self.output_call_option_data_45['buy_price'].append(abs(float(buy_price)))
            self.output_call_option_data_45['buy_cnt'].append(abs(int(buy_cnt)))
            self.output_call_option_data_45['vol_cnt'].append(abs(int(vol_cnt)))

            self.output_call_option_data_45['Delta'].append(abs(float(Delta)))
            self.output_call_option_data_45['Gamma'].append(abs(float(Gamma)))
            self.output_call_option_data_45['Theta'].append(abs(float(Theta)))
            self.output_call_option_data_45['Vega'].append(abs(float(Vega)))
            self.output_call_option_data_45['Rho'].append(abs(float(Rho)))

            # (콜종목결제월별시세요청_45)::선물시세와 코스피200시세 강제로 0 바인딩
            self.output_call_option_data_45['future_s'].append(abs(float(0)))
            self.output_call_option_data_45['k200_s'].append(abs(float(0)))
            # (콜종목결제월별시세요청_45)::체결강도조회 강제로 0 바인딩
            self.output_call_option_data_45['deal_power'].append(abs(float(0)))

    # _opt50022_45(풋종목결제월별시세요청_45)
    def _opt50022_45(self, rqname, trcode):
        # multi data
        for i in range(self.option_price_rows_45):
            code = self._comm_get_data(trcode, "", rqname, i, "종목코드")
            option_price = self._comm_get_data(trcode, "", rqname, i, "행사가")
            run_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            sell_price = self._comm_get_data(trcode, "", rqname, i, "매도호가")
            sell_cnt = self._comm_get_data(trcode, "", rqname, i, "매도호가수량")
            buy_price = self._comm_get_data(trcode, "", rqname, i, "매수호가")
            buy_cnt = self._comm_get_data(trcode, "", rqname, i, "매수호가수량")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "누적거래량")

            Delta = self._comm_get_data(trcode, "", rqname, i, "델타")
            Gamma = self._comm_get_data(trcode, "", rqname, i, "감마")
            Theta = self._comm_get_data(trcode, "", rqname, i, "세타")
            Vega = self._comm_get_data(trcode, "", rqname, i, "베가")
            Rho = self._comm_get_data(trcode, "", rqname, i, "로")

            # 최상단과 최하단의 매수도호가는 공백임
            if (sell_price == '') or (buy_price == ''):
                sell_price = 0
                buy_price = 0

            self.output_put_option_data_45['code'].append(str(code))
            self.output_put_option_data_45['option_price'].append(str(option_price))
            self.output_put_option_data_45['run_price'].append(abs(float(run_price)))
            self.output_put_option_data_45['sell_price'].append(abs(float(sell_price)))
            self.output_put_option_data_45['sell_cnt'].append(abs(int(sell_cnt)))
            self.output_put_option_data_45['buy_price'].append(abs(float(buy_price)))
            self.output_put_option_data_45['buy_cnt'].append(abs(int(buy_cnt)))
            self.output_put_option_data_45['vol_cnt'].append(abs(int(vol_cnt)))

            self.output_put_option_data_45['Delta'].append(abs(float(Delta)))
            self.output_put_option_data_45['Gamma'].append(abs(float(Gamma)))
            self.output_put_option_data_45['Theta'].append(abs(float(Theta)))
            self.output_put_option_data_45['Vega'].append(abs(float(Vega)))
            self.output_put_option_data_45['Rho'].append(abs(float(Rho)))

            # (풋종목결제월별시세요청_45)::선물시세와 코스피200시세 강제로 0 바인딩
            self.output_put_option_data_45['future_s'].append(abs(float(0)))
            self.output_put_option_data_45['k200_s'].append(abs(float(0)))
            # (풋종목결제월별시세요청_45)::체결강도조회 강제로 0 바인딩
            self.output_put_option_data_45['deal_power'].append(abs(float(0)))

    # _opw20015(옵션매도주문증거금)
    def _opw20015(self, rqname, trcode):
        # 조회건수
        option_s_sell_deposit_money_rows = self._get_repeat_cnt(trcode, rqname)

        # option_s_sell_deposit_money_data
        # 인스턴스 변수 선언
        self.option_s_sell_deposit_money_output()

        #
        item_code = self._comm_get_data(trcode, "", rqname, 0, "종목코드")
        atm_option_price = self._comm_get_data(trcode, "", rqname, 0, "ATM행사가격")
        position_s = self._comm_get_data(trcode, "", rqname, 0, "위치")
        list_cnt = self._comm_get_data(trcode, "", rqname, 0, "조회건수")

        # multi data
        for i in range(option_s_sell_deposit_money_rows):
            call_adj_price = self._comm_get_data(trcode, "", rqname, i, "콜조정이론가")
            call_max_price = self._comm_get_data(trcode, "", rqname, i, "콜최대이론가")
            call_yesday_price = self._comm_get_data(trcode, "", rqname, i, "콜전일종가")
            call_sell_order_deposit_money = self._comm_get_data(trcode, "", rqname, i, "콜주문증거금")
            option_price = self._comm_get_data(trcode, "", rqname, i, "행사가격")
            put_sell_order_deposit_money = self._comm_get_data(trcode, "", rqname, i, "풋주문증거금")
            put_yesday_price = self._comm_get_data(trcode, "", rqname, i, "풋전일종가")
            put_max_price = self._comm_get_data(trcode, "", rqname, i, "풋최대이론가")
            put_adj_price = self._comm_get_data(trcode, "", rqname, i, "풋조정이론가")

            self.option_s_sell_deposit_money_data['call_adj_price'].append(abs(int(call_adj_price)))
            self.option_s_sell_deposit_money_data['call_max_price'].append(abs(int(call_max_price)))

            call_yesday_price_int = abs(int(call_yesday_price))
            call_yesday_price_flaat = call_yesday_price_int / 100
            # print(call_yesday_price_flaat)
            self.option_s_sell_deposit_money_data['call_yesday_price'].append(abs(float(call_yesday_price_flaat)))

            self.option_s_sell_deposit_money_data['call_sell_order_deposit_money'].append(abs(int(call_sell_order_deposit_money)))
            option_price_int = abs(int(option_price))
            option_price_str = str(option_price_int)
            option_price_ch = option_price_str[-5:-2] + '.' + option_price_str[-2:]
            self.option_s_sell_deposit_money_data['option_price'].append(option_price_ch)
            self.option_s_sell_deposit_money_data['put_sell_order_deposit_money'].append(abs(int(put_sell_order_deposit_money)))

            put_yesday_price_int = abs(int(put_yesday_price))
            put_yesday_price_float = put_yesday_price_int / 100
            # print(put_yesday_price_float)
            self.option_s_sell_deposit_money_data['put_yesday_price'].append(abs(float(put_yesday_price_float)))

            self.option_s_sell_deposit_money_data['put_max_price'].append(abs(int(put_max_price)))
            self.option_s_sell_deposit_money_data['put_adj_price'].append(abs(int(put_adj_price)))

        self.printt('# 서버에서 수신받은 옵션매도주문증거금')
        self.printt(self.option_s_sell_deposit_money_data)

    # _opt20002(업종별주가요청)
    def _opt20002(self, rqname, trcode):
        stock_data_rows = self._get_repeat_cnt(trcode, rqname)
        # multi data
        for i in range(stock_data_rows):
            stock_no = self._comm_get_data(trcode, "", rqname, i, "종목코드")
            stock_name = self._comm_get_data(trcode, "", rqname, i, "종목명")
            run_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            stock_vol_cnt = self._comm_get_data(trcode, "", rqname, i, "현재거래량")
            stock_sell_price = self._comm_get_data(trcode, "", rqname, i, "매도호가")
            stock_buy_price = self._comm_get_data(trcode, "", rqname, i, "매수호가")

# _opw00018(계좌평가잔고내역요청[stock])
    def _opw00018(self, rqname, trcode):
        stock_data_rows = self._get_repeat_cnt(trcode, rqname)
        # print(stock_data_rows)

        # 인스턴스 변수 선언
        self.stock_have_data_reset_output()

        total_purchase_price = self._comm_get_data(trcode, "", rqname, 0, "총매입금액")
        # self.total_purchase_price = abs(int(total_purchase_price))
        total_eval_price = self._comm_get_data(trcode, "", rqname, 0, "총평가금액")
        self.total_eval_price = abs(int(total_eval_price))
        total_eval_profit_loss_price = self._comm_get_data(trcode, "", rqname, 0, "총평가손익금액")
        total_earning_rate = self._comm_get_data(trcode, "", rqname, 0, "총수익률(%)")
        estimated_deposit = self._comm_get_data(trcode, "", rqname, 0, "추정예탁자산")
        self.estimated_deposit = abs(int(estimated_deposit))

        # multi data
        for i in range(stock_data_rows):
            stock_no_A = self._comm_get_data(trcode, "", rqname, i, "종목번호")
            stock_name = self._comm_get_data(trcode, "", rqname, i, "종목명")
            market_in_price = self._comm_get_data(trcode, "", rqname, i, "매입가")
            myhave_cnt = self._comm_get_data(trcode, "", rqname, i, "보유수량")
            run_price = self._comm_get_data(trcode, "", rqname, i, "현재가")

            # 종목코드 앞에 A 제거
            stock_no = stock_no_A[-6:]
            self.stock_have_data['stock_no'].append(str(stock_no))
            self.stock_have_data['stock_name'].append(str(stock_name))
            self.stock_have_data['market_in_price'].append(abs(int(market_in_price)))
            self.stock_have_data['myhave_cnt'].append(abs(int(myhave_cnt)))
            self.stock_have_data['run_price'].append(abs(int(run_price)))

        # 서버에서 수신받은 stock_data
        self.printt('# 서버에서 수신받은 stock_data')
        self.printt(len(self.stock_have_data['stock_no']))
        self.printt(self.stock_have_data)

        # -----
        # 추정예탁자산/총평가금액
        self.printt('# 추정예탁자산 :: only stock(전체자신의 2/12 수동으로 수시로 맞추기)')   #  :: 202209 전략수정 (자산배정 참조)
        self.printt(format(self.estimated_deposit, ','))
        self.printt('# 총평가금액')
        self.printt(format(self.total_eval_price, ','))

        # 총평가금액
        # self.total_eval_price
        # 주문가능 금액 = 추정예탁자산 - 총평가금액
        self.buy_able_money = int(self.estimated_deposit - self.total_eval_price)
        self.printt('self.buy_able_money')
        self.printt(format(self.buy_able_money, ','))

        # 1회 stock 투입금액 ::=> 20220610 :: 추정예탁자산(self.estimated_deposit)의 10%로 결정
        self.market_in_percent_won = int(math.floor(self.estimated_deposit / Future_s_Leverage_Int))
        self.printt('self.market_in_percent_won')
        self.printt(format(self.market_in_percent_won, ','))
        # -----

    # _opt50033(영업일기준잔존일)
    def _opt50033(self, rqname, trcode):
        day_residue = self._comm_get_data(trcode, "", rqname, 0, "영업일기준잔존일")

        # -----
        # 공백은 int,  float 모두 형변환시 에러 발생함
        if day_residue != '':
            day_residue_int = abs(int(day_residue))
        elif day_residue == '':
            day_residue_int = 0
        # -----

        # 당월물
        for i in range(self.option_price_rows):
            self.output_call_option_data['day_residue'].append(day_residue_int)
            self.output_put_option_data['day_residue'].append(day_residue_int)
        # 차월물
        for i in range(self.option_price_rows_45):
            self.output_call_option_data_45['day_residue'].append(day_residue_int)
            self.output_put_option_data_45['day_residue'].append(day_residue_int)

    # 선옵잔고요청
    def _opt50027(self, rqname, trcode):
        myhave_rows = self._get_repeat_cnt(trcode, rqname)

        # -----
        # 선옵잔고요청 변수선언
        # 주문시 선옵잔고 변수 초기화
        self.reset_myhave_var()
        # -----

        for i in range(myhave_rows):
            code = self._comm_get_data(trcode, "", rqname, i, "종목코드")
            item_name = self._comm_get_data(trcode, "", rqname, i, "종목명")
            myhave_cnt = self._comm_get_data(trcode, "", rqname, i, "보유수량")
            sell_or_buy = self._comm_get_data(trcode, "", rqname, i, "매매구분")

            if myhave_cnt != '0':
                self.option_myhave['code'].append(str(code))
                self.option_myhave['myhave_cnt'].append(abs(int(myhave_cnt)))
                self.option_myhave['sell_or_buy'].append(abs(int(sell_or_buy)))

        # -----
        # 선옵잔고요청
        self.printt('self.option_myhave')
        self.printt(self.option_myhave)
        # -----

    # 예탁금및증거금조회
    def _opw20010(self, rqname, trcode):
        # 변수선언
        self.option_mymoney = {'deposit_money': [], 'margin_call': [], 'order_able': [], 'total_money': []}

        DepositTotal = self._comm_get_data(trcode, "", rqname, '0', "예탁총액")
        MarginTotal = self._comm_get_data(trcode, "", rqname, '0', "증거금총액")
        OrderAbleTotal = self._comm_get_data(trcode, "", rqname, '0', "주문가능총액")
        RunMyTotalMoney = self._comm_get_data(trcode, "", rqname, '0', "순자산금액")

        self.option_mymoney['deposit_money'].append(Kiwoom.change_format(DepositTotal))
        self.option_mymoney['margin_call'].append(Kiwoom.change_format(MarginTotal))
        self.option_mymoney['order_able'].append(Kiwoom.change_format(OrderAbleTotal))
        self.option_mymoney['total_money'].append(Kiwoom.change_format(RunMyTotalMoney))

        # option_have_money(순자산금액)
        option_have_money = abs(float(RunMyTotalMoney))
        self.option_have_money = abs(int(option_have_money))
        # 주문가능총액
        option_order_able_money = abs(float(OrderAbleTotal))
        self.option_order_able_money = abs(int(option_order_able_money))

        # -----
        self.printt('self.option_mymoney')
        self.printt(self.option_mymoney)
        # -----

    # 선옵계좌별주문가능수량요청
    def _opw20009(self, rqname, trcode):
        new_order_able_cnt = self._comm_get_data(trcode, "", rqname, '0', "신규가능수량")
        order_able_cash = self._comm_get_data(trcode, "", rqname, '0', "주문가능현금")

        # 신규가능수량
        self.future_s_option_s_new_order_able_cnt = abs(int(new_order_able_cnt))
        self.printt('self.future_s_option_s_new_order_able_cnt')
        self.printt(format(self.future_s_option_s_new_order_able_cnt, ','))
        # 주문가능현금
        self.order_able_cash = abs(int(order_able_cash))
        self.printt('self.future_s_option_s_order_able_cash')
        self.printt(format(self.order_able_cash, ','))

    # 선물월차트요청
    def _opt50072(self, rqname, trcode):
        future_s_shlc_month_data_rows = self._get_repeat_cnt(trcode, rqname)

        # 인스턴스 변수 선언
        self.future_s_chain_shlc_month_reset_output()

        # multi data
        for i in range(future_s_shlc_month_data_rows):
            future_s_date = self._comm_get_data(trcode, "", rqname, i, "일자")
            future_s_start = self._comm_get_data(trcode, "", rqname, i, "시가")
            future_s_high = self._comm_get_data(trcode, "", rqname, i, "고가")
            future_s_low = self._comm_get_data(trcode, "", rqname, i, "저가")
            future_s_end = self._comm_get_data(trcode, "", rqname, i, "현재가")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "누적거래량")

            self.output_future_s_chain_shlc_month_data['stock_date'].append(str(future_s_date[:8]))
            self.output_future_s_chain_shlc_month_data['stock_start'].append(abs(float(future_s_start)))
            self.output_future_s_chain_shlc_month_data['stock_high'].append(abs(float(future_s_high)))
            self.output_future_s_chain_shlc_month_data['stock_low'].append(abs(float(future_s_low)))
            self.output_future_s_chain_shlc_month_data['stock_end'].append(abs(float(future_s_end)))
            self.output_future_s_chain_shlc_month_data['vol_cnt'].append(abs(int(vol_cnt)))

    # 선물일차트요청
    def _OPT50030(self, rqname, trcode):
        future_s_shlc_day_data_rows = self._get_repeat_cnt(trcode, rqname)

        # 인스턴스 변수 선언
        self.future_s_chain_shlc_day_reset_output()

        # multi data
        for i in range(future_s_shlc_day_data_rows):
            future_s_date = self._comm_get_data(trcode, "", rqname, i, "일자")
            future_s_start = self._comm_get_data(trcode, "", rqname, i, "시가")
            future_s_high = self._comm_get_data(trcode, "", rqname, i, "고가")
            future_s_low = self._comm_get_data(trcode, "", rqname, i, "저가")
            future_s_end = self._comm_get_data(trcode, "", rqname, i, "현재가")

            self.output_future_s_chain_shlc_day_data['stock_date'].append(str(future_s_date))
            self.output_future_s_chain_shlc_day_data['stock_start'].append(abs(float(future_s_start)))
            self.output_future_s_chain_shlc_day_data['stock_high'].append(abs(float(future_s_high)))
            self.output_future_s_chain_shlc_day_data['stock_low'].append(abs(float(future_s_low)))
            self.output_future_s_chain_shlc_day_data['stock_end'].append(abs(float(future_s_end)))

    # 주식월봉차트조회요청
    def _opt10083(self, rqname, trcode):
        stock_shlc_month_data_rows = self._get_repeat_cnt(trcode, rqname)

        # 인스턴스 변수 선언
        self.stock_shlc_month_reset_output()

        # multi data
        for i in range(stock_shlc_month_data_rows):
            stock_date = self._comm_get_data(trcode, "", rqname, i, "일자")
            stock_start = self._comm_get_data(trcode, "", rqname, i, "시가")
            stock_high = self._comm_get_data(trcode, "", rqname, i, "고가")
            stock_low = self._comm_get_data(trcode, "", rqname, i, "저가")
            stock_end = self._comm_get_data(trcode, "", rqname, i, "현재가")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "거래량")

            self.output_stock_shlc_month_data['stock_date'].append(str(stock_date))
            self.output_stock_shlc_month_data['stock_start'].append(abs(int(stock_start)))
            self.output_stock_shlc_month_data['stock_high'].append(abs(int(stock_high)))
            self.output_stock_shlc_month_data['stock_low'].append(abs(int(stock_low)))
            self.output_stock_shlc_month_data['stock_end'].append(abs(int(stock_end)))
            self.output_stock_shlc_month_data['vol_cnt'].append(abs(int(vol_cnt)))

    # 주식일봉차트조회요청
    def _opt10081(self, rqname, trcode):
        stock_shlc_data_rows = self._get_repeat_cnt(trcode, rqname)

        # 인스턴스 변수 선언
        self.stock_shlc_day_reset_output()

        # multi data
        for i in range(stock_shlc_data_rows):
            stock_date = self._comm_get_data(trcode, "", rqname, i, "일자")
            stock_start = self._comm_get_data(trcode, "", rqname, i, "시가")
            stock_high = self._comm_get_data(trcode, "", rqname, i, "고가")
            stock_low = self._comm_get_data(trcode, "", rqname, i, "저가")
            stock_end = self._comm_get_data(trcode, "", rqname, i, "현재가")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "거래량")

            self.output_stock_shlc_day_data['stock_date'].append(str(stock_date))
            self.output_stock_shlc_day_data['stock_start'].append(abs(int(stock_start)))
            self.output_stock_shlc_day_data['stock_high'].append(abs(int(stock_high)))
            self.output_stock_shlc_day_data['stock_low'].append(abs(int(stock_low)))
            self.output_stock_shlc_day_data['stock_end'].append(abs(int(stock_end)))
            self.output_stock_shlc_day_data['vol_cnt'].append(abs(int(vol_cnt)))

            # 주식일봉차트조회요청 => c_to_cf_hand 전용
            if i == 0:  # 마지막 날자만 기록
                self.stock_item_data['stock_start'].append(abs(int(stock_start)))
                self.stock_item_data['stock_high'].append(abs(int(stock_high)))
                self.stock_item_data['stock_low'].append(abs(int(stock_low)))
                self.stock_item_data['stock_end'].append(abs(int(stock_end)))
                self.stock_item_data['vol_cnt'].append(abs(int(vol_cnt)))

    # 체결강도조회
    def _optkwfid(self, rqname, trcode):
        deal_power_rows = self._get_repeat_cnt(trcode, rqname)
        # multi data
        for kw in range(deal_power_rows):
            stock_no = self._comm_get_data(trcode, "", rqname, kw, "종목코드")
            stock_name = self._comm_get_data(trcode, "", rqname, kw, "종목명")
            stock_start = self._comm_get_data(trcode, "", rqname, kw, "시가")
            stock_high = self._comm_get_data(trcode, "", rqname, kw, "고가")
            stock_low = self._comm_get_data(trcode, "", rqname, kw, "저가")
            stock_end = self._comm_get_data(trcode, "", rqname, kw, "현재가")
            vol_cnt = self._comm_get_data(trcode, "", rqname, kw, "거래량")

            # 주식일봉차트조회요청 => c_to_cf_hand 전용(실시간 처리)
            for i in range(len(self.stock_item_data['stock_item_no'])):
                if stock_no == self.stock_item_data['stock_item_no'][i]:
                    self.stock_item_data['stock_item_name'][i] = str(stock_name)
                    self.stock_item_data['stock_start'][i] = (abs(int(stock_start)))
                    self.stock_item_data['stock_high'][i] = (abs(int(stock_high)))
                    self.stock_item_data['stock_low'][i] = (abs(int(stock_low)))
                    self.stock_item_data['stock_end'][i] = (abs(int(stock_end)))
                    self.stock_item_data['vol_cnt'][i] = (abs(int(vol_cnt)))

        self.printt('self.stock_item_data')
        self.printt(len(self.stock_item_data['stock_item_no']))
        self.printt(self.stock_item_data)
        self.printt('체결강도조회 모두 완료')

    # stock
    # TR을 통해 얻어온 데이터를 인스턴스 변수 초기화
    def stock_shlc_month_reset_output(self):
        self.output_stock_shlc_month_data = {'stock_date': [], 'stock_start': [], 'stock_high': [], 'stock_low': [],
                                        'stock_end': [], 'vol_cnt': []}
    def stock_shlc_day_reset_output(self):
        self.output_stock_shlc_day_data = {'stock_date': [], 'stock_start': [], 'stock_high': [], 'stock_low': [],
                                        'stock_end': [], 'vol_cnt': []}

    # futrue_s 선물
    # TR을 통해 얻어온 데이터를 인스턴스 변수 초기화
    def future_s_chain_shlc_month_reset_output(self):
        self.output_future_s_chain_shlc_month_data = {'stock_date': [], 'stock_start': [], 'stock_high': [], 'stock_low': [],
                                        'stock_end': [], 'vol_cnt': []}
    def future_s_chain_shlc_day_reset_output(self):
        self.output_future_s_chain_shlc_day_data = {'stock_date': [], 'stock_start': [], 'stock_high': [], 'stock_low': [],
                                        'stock_end': [], 'vol_cnt': []}
    # TR을 통해 얻어온 데이터를 인스턴스 변수에 저장
    def futrue_s_reset_output(self):
        self.futrue_s_data = {'item_code': [], 'item_name': [], 'run_price': [], 'sell_price': [], 'buy_price': [], 'vol_cnt': [],
                                        'start_price': [], 'high_price': [], 'low_price': [], 'theorist_price': [],
                                        'market_basis': [], 'theorist_basis': [], 'kospi_trans': [], 'day_residue': []}
        # 차월물
        self.futrue_s_data_45 = {'item_code': [], 'item_name': [], 'run_price': [], 'sell_price': [], 'buy_price': [], 'vol_cnt': [],
                                        'start_price': [], 'high_price': [], 'low_price': [], 'theorist_price': [],
                                        'market_basis': [], 'theorist_basis': [], 'kospi_trans': [], 'day_residue': []}

    # option
    # TR을 통해 얻어온 데이터를 인스턴스 변수에 저장
    def option_reset_output(self):
        self.output_call_option_data = {'code': [], 'option_price': [], 'run_price': [], 'sell_price': [],
                                        'sell_cnt': [], 'buy_price': [], 'buy_cnt': [], 'vol_cnt': [],
                                        'Delta': [], 'Gamma': [], 'Theta': [], 'Vega': [], 'Rho': [],
                                        'future_s': [], 'k200_s': [], 'day_residue': [], 'deal_power': []}
        self.output_put_option_data = {'code': [], 'option_price': [], 'run_price': [], 'sell_price': [],
                                       'sell_cnt': [], 'buy_price': [], 'buy_cnt': [], 'vol_cnt': [],
                                       'Delta': [], 'Gamma': [], 'Theta': [], 'Vega': [], 'Rho': [],
                                       'future_s': [], 'k200_s': [], 'day_residue': [], 'deal_power': []}
        # 차월물
        self.output_call_option_data_45 = {'code': [], 'option_price': [], 'run_price': [], 'sell_price': [],
                                        'sell_cnt': [], 'buy_price': [], 'buy_cnt': [], 'vol_cnt': [],
                                        'Delta': [], 'Gamma': [], 'Theta': [], 'Vega': [], 'Rho': [],
                                        'future_s': [], 'k200_s': [], 'day_residue': [], 'deal_power': []}
        self.output_put_option_data_45 = {'code': [], 'option_price': [], 'run_price': [], 'sell_price': [],
                                       'sell_cnt': [], 'buy_price': [], 'buy_cnt': [], 'vol_cnt': [],
                                       'Delta': [], 'Gamma': [], 'Theta': [], 'Vega': [], 'Rho': [],
                                       'future_s': [], 'k200_s': [], 'day_residue': [], 'deal_power': []}
    # option_s_sell_deposit_money
    # TR을 통해 얻어온 데이터를 인스턴스 변수에 저장
    def option_s_sell_deposit_money_output(self):
        # 당월물/차월물
        # 서버구분(모의서버 : '1' /실서버 : '')
        if self.get_server_gubun() == '':
            self.option_s_sell_deposit_money_data = {'call_adj_price': [], 'call_max_price': [], 'call_yesday_price': [], 'call_sell_order_deposit_money': [],
                                        'option_price': [], 'put_sell_order_deposit_money': [], 'put_yesday_price': [], 'put_max_price': [],
                                        'put_adj_price': []}

        # 모의서버 일때 임의의 값 넣어줌
        elif self.get_server_gubun() == '1':
            self.option_s_sell_deposit_money_data = {'call_adj_price': [86208, 99000, 112569, 142293, 172159, 202166, 240590, 306626, 372899, 449662, 576939, 704605, 884423, 1110511, 1368252, 1739311, 2145492, 2712323, 3367830, 3958940, 5109829, 6413693, 7712998, 9274849, 11264804, 13117768, 15309970, 17631546, 20037962, 22511864, 25006229, 27505009, 30004447, 32503941, 35003437, 37502933, 40002429, 42501925, 45001421, 47500917, 50000413, 52499909, 54999404, 57498900, 59998396, 62497892, 64997388, 67496884, 69996380, 72495876, 74995372, 77494868, 79994364, 82493860, 84993356, 87492852, 89992348, 92491844, 94991340, 97490835, 99990331, 102489827, 104989323, 107488819, 109988315, 112487811, 114987307, 117486803, 119986299, 122485795, 124985291, 127484787, 129984283, 132483779, 134983275, 137482771, 139982266, 142481762, 144981258, 147480754, 149980250, 152479746, 154979242, 157478738, 159978234, 162477730, 164977226, 167476722, 169976218, 172475714, 174975210, 177474706, 179974202, 182473697, 184973193, 187472689, 189972185, 192471681, 194971177, 197470673, 199970169, 202469665, 204969161, 207468657, 209968153, 212467649, 214967145, 217466641, 219966137, 222465633, 224965128, 227464624, 229964120], 'call_max_price': [12112, 13126, 14160, 15212, 16282, 17371, 18479, 19909, 23971, 28073, 32216, 36401, 40681, 46065, 57336, 68695, 80144, 91682, 116631, 106273, 158779, 234860, 271787, 309173, 500399, 500276, 629761, 822541, 920320, 1206903, 1614339, 2184097, 2978545, 4252989, 5774200, 7537189, 9575922, 11883187, 14293266, 16764634, 19253695, 21751806, 24251020, 26750494, 29249986, 31749482, 34248978, 36748474, 39247970, 41747466, 44246962, 46746458, 49245954, 51745450, 54244946, 56744442, 59243938, 61743434, 64242930, 66742425, 69241921, 71741417, 74240915, 76740413, 79239910, 81739407, 84238908, 86738408, 89237909, 91737392, 94236885, 96736378, 99235873, 101735369, 104234865, 106734361, 109233856, 111733352, 114232848, 116732344, 119231840, 121731336, 124230832, 126730328, 129229824, 131729320, 134228816, 136728312, 139227808, 141727304, 144226800, 146726296, 149225792, 151725287, 154224783, 156724279, 159223775, 161723271, 164222767, 166722263, 169221759, 171721255, 174220751, 176720247, 179219743, 181719239, 184218735, 186718231, 189217727, 191717223, 194216718, 196716214, 199215710], 'call_yesday_price': [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.09, 0.15, 0.27, 0.4, 0.69, 1.09, 1.79, 2.62, 3.9, 5.23, 6.99, 9.01, 11.35, 13.5, 15.9, 18.5, 20.9, 22.5, 25.85, 27.35, 30.45, 33.0, 36.05, 38.55, 41.05, 42.1, 46.1, 48.55, 51.05, 53.55, 56.05, 56.7, 57.6, 59.5, 60.5, 68.55, 71.05, 73.55, 76.05, 78.55, 81.05, 83.55, 86.05, 88.55, 91.05, 93.55, 96.05, 98.55, 101.05, 103.55, 106.05, 108.55, 111.05, 113.55, 116.05, 118.5, 121.0, 123.5, 126.0, 128.5, 131.0, 133.5, 136.0, 138.5, 141.0, 143.5, 146.0, 148.5, 151.0, 153.5, 156.0, 158.5, 161.0, 163.5, 166.0, 167.9], 'call_sell_order_deposit_money': [250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 251837, 296171, 382487, 480277, 577725, 694864, 844110, 983083, 1147498, 1321616, 1502097, 1687640, 1874717, 2062126, 2249584, 2436296, 2623008, 2809720, 2996432, 3180894, 3535817, 4123659, 4713424, 5265452, 5790255, 6240124, 6657497, 6962371, 7254745, 7439619, 7559493, 7599367, 7686741, 7711615, 7686489, 7711363, 7936237, 7723611, 7973485, 7823359, 7810733, 7673106, 7672980, 7672854, 8035229, 7660103, 7672478, 7672352, 7672227, 7672102, 8134477, 8534348, 8684221, 9059095, 7671468, 7671342, 7671216, 7671090, 7670964, 7670838, 7670712, 7670586, 7670460, 7670334, 7670208, 7670082, 7669956, 7669830, 7669704, 7669578, 7669452, 7669326, 7669200, 7669074, 7681448, 7681322, 7681196, 7681070, 7680944, 7680818, 7680692, 7680566, 7680440, 7680314, 7680188, 7680062, 7679936, 7679810, 7679684, 7679558, 7679432, 7679306, 7679180, 7679054, 7828928], 'option_price': ['465.00', '462.50', '460.00', '457.50', '455.00', '452.50', '450.00', '447.50', '445.00', '442.50', '440.00', '437.50', '435.00', '432.50', '430.00', '427.50', '425.00', '422.50', '420.00', '417.50', '415.00', '412.50', '410.00', '407.50', '405.00', '402.50', '400.00', '397.50', '395.00', '392.50', '390.00', '387.50', '385.00', '382.50', '380.00', '377.50', '375.00', '372.50', '370.00', '367.50', '365.00', '362.50', '360.00', '357.50', '355.00', '352.50', '350.00', '347.50', '345.00', '342.50', '340.00', '337.50', '335.00', '332.50', '330.00', '327.50', '325.00', '322.50', '320.00', '317.50', '315.00', '312.50', '310.00', '307.50', '305.00', '302.50', '300.00', '297.50', '295.00', '292.50', '290.00', '287.50', '285.00', '282.50', '280.00', '277.50', '275.00', '272.50', '270.00', '267.50', '265.00', '262.50', '260.00', '257.50', '255.00', '252.50', '250.00', '247.50', '245.00', '242.50', '240.00', '237.50', '235.00', '232.50', '230.00', '227.50', '225.00', '222.50', '220.00', '217.50', '215.00', '212.50', '210.00', '207.50', '205.00', '202.50', '200.00', '197.50', '195.00', '192.50', '190.00', '187.50', '185.00'], 'put_sell_order_deposit_money': [7531211, 7706327, 7706443, 7706559, 7706680, 7706803, 7706926, 7707050, 7707174, 7707299, 7707425, 7707550, 7145176, 7707802, 7320429, 7708055, 7708180, 7708306, 7708432, 7708558, 7708684, 7708810, 7708936, 7709062, 7709188, 7709314, 7709440, 7709566, 7709692, 7709818, 7709944, 7210070, 7710196, 7710322, 7635448, 7710574, 7710700, 7710826, 7623452, 7511078, 7511204, 7473830, 7393957, 7124083, 7006709, 6686835, 6324461, 5879588, 5384723, 4824969, 4250700, 3653729, 3217446, 3032234, 2845521, 2660309, 2473597, 2286135, 2098673, 1911218, 1724534, 1537331, 1350963, 1167654, 989352, 822409, 670367, 530529, 414463, 324549, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000, 250000], 'put_yesday_price': [112.1, 108.9, 106.4, 103.9, 101.4, 98.9, 96.4, 93.9, 91.4, 88.9, 86.4, 83.9, 83.65, 78.9, 77.95, 73.9, 71.4, 68.9, 66.4, 63.9, 61.4, 58.9, 56.4, 53.9, 51.4, 48.9, 46.4, 43.9, 41.4, 38.9, 36.4, 35.9, 31.4, 28.9, 26.7, 23.9, 21.4, 18.9, 16.75, 14.7, 12.2, 9.85, 7.67, 6.25, 4.22, 3.0, 1.95, 1.23, 0.71, 0.45, 0.25, 0.15, 0.1, 0.07, 0.06, 0.03, 0.02, 0.02, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01], 'put_max_price': [142224845, 139725308, 137225771, 134726235, 132226718, 129727211, 127227704, 124728198, 122228696, 119729197, 117229699, 114730201, 112230705, 109731209, 107231715, 104732218, 102232721, 99733225, 97233729, 94734233, 92234737, 89735240, 87235744, 84736249, 82236753, 79737257, 77237761, 74738265, 72238769, 69739273, 67239777, 64740281, 62240785, 59741289, 57241793, 54742297, 52242801, 49743305, 47243809, 44744313, 42244817, 39745321, 37245826, 34746330, 32246834, 29747338, 27247842, 24748352, 22248890, 19749876, 17252799, 14764916, 12321659, 9980657, 7868118, 5882167, 4293656, 3138262, 2292225, 1666303, 1053588, 738124, 524252, 391165, 269565, 209263, 153255, 105527, 77448, 68318, 56738, 32804, 32084, 27015, 20124, 13506, 9742, 8571, 7397, 6151, 5312, 4943, 4552, 4139, 3724, 3287, 2834, 1670, 998, 516, 311, 141, 85, 34, 20, 7, 4, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 'put_adj_price': [172973065, 170473569, 167974073, 165474577, 162975081, 160475585, 157976089, 155476593, 152977098, 150477602, 147978106, 145478610, 142979114, 140479618, 137980122, 135480626, 132981130, 130481634, 127982138, 125482642, 122983146, 120483650, 117984154, 115484658, 112985162, 110485667, 107986171, 105486675, 102987179, 100487683, 97988187, 95488691, 92989195, 90489699, 87990203, 85490707, 82991211, 80491715, 77992219, 75492723, 72993227, 70493731, 67994236, 65494740, 62995244, 60495748, 57996252, 55496756, 52997260, 50497764, 47998268, 45498772, 42999276, 40499780, 38000284, 35500788, 33001292, 30501796, 28002304, 25502900, 23003781, 20507746, 18022839, 15578726, 13201361, 10975453, 8948222, 7083724, 5536171, 4337315, 3295769, 2355652, 1853431, 1367102, 955114, 693916, 462875, 335841, 252575, 185047, 137657, 104652, 73934, 58858, 43755, 31828, 25496, 13218, 8046, 4027, 2105, 1052, 422, 225, 88, 34, 15, 4, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}

    # stock
    # TR을 통해 얻어온 데이터를 인스턴스 변수에 저장
    def stock_deal_power_reset_output(self):
        self.deal_power_data = {'stock_no': [], 'stock_name': [], 'run_price': [], 'sell_price': [], 'sell_cnt': [],
                                'buy_price': [], 'buy_cnt': [], 'vol_cnt': [], 'deal_power': []}
    def stock_have_data_reset_output(self):
        self.stock_have_data = {'stock_no': [], 'stock_name': [], 'market_in_price': [], 'myhave_cnt': [], 'run_price': []}

# 이벤트 슬롯
    # 선물전체시세요청 - 이벤트 슬롯
    def futrue_s_data_rq(self):
        # 선물전체시세요청
        sID = "종목코드"
        get_future_s_code_list = self.kiwoom.get_future_s_list()
        # print(get_future_s_code_list)
        sValue = get_future_s_code_list[0]
        sRQName = "선물전체시세요청"
        sTrCode = "OPTFOFID"
        nPrevNext = 0
        sScreenNo = "1010"
        # 서버요청
        self.printt('# 선물전체시세요청 전송_당월물')
        self.server_set_rq_future_s_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)

        # 차월물
        # 선물전체시세요청
        sID = "종목코드"
        get_future_s_code_list = self.kiwoom.get_future_s_list()
        # print(get_future_s_code_list)
        sValue = get_future_s_code_list[1]
        sRQName = "선물전체시세요청_45"
        sTrCode = "OPTFOFID"
        nPrevNext = 0
        sScreenNo = "1010"
        # 서버요청
        self.printt('# 선물전체시세요청 전송_차월물')
        self.server_set_rq_future_s_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)

        # -----
        # 서버에서 수신받은 선물전체시세 데이터
        self.printt('# 서버에서 수신받은 선물전체시세 데이터')
        self.printt(self.futrue_s_data)
        # 차월물
        self.printt(self.futrue_s_data_45)

        # 영업일 기준 잔존일
        future_s_day_residue_int = self.futrue_s_data['day_residue'][0]
        self.future_s_day_residue_str = str(future_s_day_residue_int)
        self.printt('# 서버에서 수신받은 영업일 기준 잔존일_당월물')
        self.printt(self.future_s_day_residue_str)
        future_s_45_day_residue_int = self.futrue_s_data_45['day_residue'][0]
        self.future_s_45_day_residue_str = str(future_s_45_day_residue_int)
        self.printt('# 서버에서 수신받은 영업일 기준 잔존일_차월물')
        self.printt(self.future_s_45_day_residue_str)
        # -----

    # 콜/풋 월별시세요청 - 이벤트 슬롯
    def call_put_data_rq(self):
        # 콜종목결제월별시세요청
        sID = "만기년월"
        sValue = self.kiwoom.get_month_mall(0)
        self.current_monthmall_var = sValue
        sRQName = "콜종목결제월별시세요청"
        sTrCode = "OPT50021"
        nPrevNext = 0
        sScreenNo = "0021"
        # 서버요청
        self.printt('# 콜종목결제월별시세요청 전송')
        self.server_set_rq_call_put_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)

        # 풋종목결제월별시세요청
        sID = "만기년월"
        sValue = self.kiwoom.get_month_mall(0)
        self.current_monthmall_var = sValue
        sRQName = "풋종목결제월별시세요청"
        sTrCode = "OPT50022"
        nPrevNext = 0
        sScreenNo = "0022"
        # 서버요청
        self.printt('# 풋종목결제월별시세요청 전송')
        self.server_set_rq_call_put_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)

        # 차월물
        # 콜종목결제월별시세요청_45
        sID = "만기년월"
        sValue = self.kiwoom.get_month_mall(1)
        # self.current_monthmall_var = sValue
        sRQName = "콜종목결제월별시세요청_45"
        sTrCode = "OPT50021"
        nPrevNext = 0
        sScreenNo = "0021"
        # 서버요청
        self.printt('# 콜종목결제월별시세요청_45 전송')
        self.server_set_rq_call_put_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)

        # 풋종목결제월별시세요청_45
        sID = "만기년월"
        sValue = self.kiwoom.get_month_mall(1)
        # self.current_monthmall_var = sValue
        sRQName = "풋종목결제월별시세요청_45"
        sTrCode = "OPT50022"
        nPrevNext = 0
        sScreenNo = "0022"
        # 서버요청
        self.printt('# 풋종목결제월별시세요청_45 전송')
        self.server_set_rq_call_put_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)

        # -----
        # 부팅시만 중심가 찾기
        # 당원물 중심가
        # 장중에는 옵션 'delta'를 1/4 계산해서 그 중간값에 올때까지 기다렸다가 그 시점에 중심가 변경처리
        # (대략 10/20/10 으로 분포됨 - 70 / (60)50(40) / 30)
        # 중심가 함수(부팅시에는 조정델타 없이 처리)
        center_index_option_price = self.center_option_price_for_booting_fn(self.option_price_rows,
                                                                self.output_call_option_data,
                                                                self.output_put_option_data)
        # 시간표시
        current_time = time.ctime()
        self.printt(current_time)
        self.printt('self.center_option_price_for_booting_fn')
        self.printt(center_index_option_price)
        # (True, 3, '457.50')
        self.center_index = center_index_option_price[1]
        self.center_option_price = center_index_option_price[2]
        if self.center_index != 0:
            self.printt('self.center_index != 0')
            self.printt('# 중심가 중심인덱스')
            self.printt(self.center_index)
            self.printt(self.center_option_price)
        # 장시작 최초 center_index == 0 경우
        elif self.center_index == 0:
            # 지난 옵션 헤지 비율에서 중심가 가져오기
            self.printt('elif self.center_index == 0:')
            last_option_s_center_option_price = self.option_s_center_option_price_pickup_fn()
            # 콜옵션 자료와 비교
            for i in range(len(self.output_call_option_data['code'])):
                if last_option_s_center_option_price == self.output_call_option_data['option_price'][i]:
                    self.center_index = i
                    self.center_option_price = self.output_call_option_data['option_price'][i]
            self.printt('# 중심가 중심인덱스')
            self.printt(self.center_index)
            self.printt(self.center_option_price)
            # 지난 옵션 헤지 비율에서도 중심가 공백일경우
            # 서버요청으로 중심가 찾기(어쩔수 없이)
            if self.center_option_price == '':
                # GetOptionATM() 함수 호출
                self.printt('# GetOptionATM() 함수 호출')
                option_s_atm_str = self.kiwoom.get_option_s_atm()
                # print(option_s_atm_str)
                # print(type(option_s_atm_str))
                # 콜옵션 자료와 비교
                for i in range(len(self.output_call_option_data['code'])):
                    option_price_float = float(self.output_call_option_data['option_price'][i])
                    option_price_float_mul_int = int(option_price_float * 100)
                    option_price_float_mul_int_str = str(option_price_float_mul_int)
                    # print(option_price_float_mul_int_str)
                    # print(type(option_price_float_mul_int_str))
                    if option_s_atm_str == option_price_float_mul_int_str:
                        self.center_index = i
                        self.center_option_price = self.output_call_option_data['option_price'][i]
                self.printt('# 중심가 중심인덱스')
                self.printt(self.center_index)
                self.printt(self.center_option_price)
        # 차월물 중심가
        for i in range(len(self.output_call_option_data_45['code'])):
            # str 타입의 당월 중심가와 차월 중심가 비교
            if self.center_option_price == self.output_call_option_data_45['option_price'][i]:
                self.center_index_45 = i
                self.center_option_price_45 = self.output_call_option_data_45['option_price'][i]
        self.printt('# 차월물 중심가 중심인덱스')
        self.printt(self.center_index_45)
        self.printt(self.center_option_price_45)
        # -----

        # -----
        # 선옵잔존일조회요청
        today = datetime.datetime.today().strftime("%Y%m%d")
        sID1 = "종목코드"
        sValue1 = self.output_put_option_data['code'][self.center_index]
        sID2 = "기준일자"
        sValue2 = today
        sRQName = "선옵잔존일조회요청"
        sTrCode = "OPT50033"
        nPrevNext = 0
        sScreenNo = "0033"
        # 서버요청
        self.printt('# 선옵잔존일조회요청 전송')
        self.server_set_rq_DayResidue(sID1, sValue1, sID2, sValue2, sRQName, sTrCode, nPrevNext, sScreenNo)

        # 영업일 기준 잔존일
        day_residue_int = self.output_put_option_data['day_residue'][self.center_index]
        self.day_residue_str = str(day_residue_int)
        self.printt('self.day_residue_str')
        self.printt(self.day_residue_str)
        # ----

        # -----
        # 서버에서 수신받은 콜 풋 데이터
        self.printt('# 서버에서 수신받은 콜 풋 데이터')
        self.printt(self.output_call_option_data)
        self.printt(self.output_put_option_data)
        # 차월물
        self.printt(self.output_call_option_data_45)
        self.printt(self.output_put_option_data_45)

        self.printt('# 중심가 중심인덱스')
        self.printt(self.center_index)
        self.printt(self.center_option_price)

        self.printt('# 차월물 중심가 중심인덱스')
        self.printt(self.center_index_45)
        self.printt(self.center_option_price_45)
        # -----

    # 옵션매도주문증거금 요청
    def option_s_sell_deposit_money_data_rq(self):
        # 영업일 기준 잔존일
        day_residue_int = self.output_put_option_data['day_residue'][self.center_index]
        # [ opw20015 : 옵션매도주문증거금 ]
        # if day_residue_int > 2:

        # -----
        # 옵션에서 차월물 진입을 않하면서 옵션매도주문증거금 당월물만[202402~~]
        # 당월물
        sID1 = "월물구분"
        sValue1 = self.kiwoom.get_month_mall(0)
        sID2 = "클래스구분"
        sValue2 = "01"
        sRQName = "옵션매도주문증거금"
        sTrCode = "opw20015"
        nPrevNext = "0"
        sScreenNo = "20015"
        # 서버요청
        self.printt('# 옵션매도주문증거금 전송[당월물]')
        self.server_set_rq_option_s_sell_deposit_money_data(sID1, sValue1, sID2, sValue2, sRQName, sTrCode,
                                                            nPrevNext, sScreenNo)
        # -----

        # else:
        #     # 당월물
        #     sID1 = "월물구분"
        #     sValue1 = self.kiwoom.get_month_mall(1)
        #     sID2 = "클래스구분"
        #     sValue2 = "01"
        #     sRQName = "옵션매도주문증거금"
        #     sTrCode = "opw20015"
        #     nPrevNext = "0"
        #     sScreenNo = "20015"
        #     # 서버요청
        #     self.printt('# 옵션매도주문증거금 전송[차월물]')
        #     self.server_set_rq_option_s_sell_deposit_money_data(sID1, sValue1, sID2, sValue2, sRQName, sTrCode,
        #                                                         nPrevNext, sScreenNo)

    # 업종별주가요청 시세요청 - 이벤트 슬롯
    def stock_total_data_rq(self):
        # 업종별주가요청
        # 시장구분 = 0:코스피, 1: 코스닥, 2: 코스피200
        # 업종코드 = 001:종합(KOSPI), 002: 대형주, 003: 중형주, 004: 소형주 101:
        # 종합(KOSDAQ),
        # 201: KOSPI200, 302: KOSTAR, 701: KRX100
        sID1 = "시장구분"
        sValue1 = "2"
        sID2 = "업종코드"
        sValue2 = "201"
        sRQName = "업종별주가요청"
        sTrCode = "OPT20002"
        nPrevNext = 0
        sScreenNo = "20002"
        # 서버요청
        self.server_set_rq_stock_price(sID1, sValue1, sID2, sValue2, sRQName, sTrCode, nPrevNext, sScreenNo)
        # 연속조회시
        while self.remained_data == True:
            nPrevNext = 2
            # 서버요청
            self.server_set_rq_stock_price(sID1, sValue1, sID2, sValue2, sRQName, sTrCode, nPrevNext, sScreenNo)
        self.printt('# 업종별주가요청 전송')

    # 계좌평가잔고내역요청[stock] - 이벤트 슬롯
    def stock_have_data_rq(self):
        # 계좌평가잔고내역요청[stock]
        sID1 = "계좌번호"
        sValue1 = self.comboBox_acc_stock.currentText()
        sID2 = "비밀번호"
        sValue2 = ''
        sID3 = "비밀번호입력매체구분"
        sValue3 = '00'
        sID4 = "조회구분"
        sValue4 = '1'
        sRQName = "계좌평가잔고내역요청"
        sTrCode = "opw00018"
        nPrevNext = 0
        sScreenNo = "0018"

        # 서버요청
        self.printt('# 계좌평가잔고내역요청[stock] 전송')
        self.server_set_rq_stock_have_data(sID1, sValue1, sID2, sValue2, sID3, sValue3, sID4, sValue4, sRQName, sTrCode,
                                           nPrevNext, sScreenNo)
        # 연속조회시
        while self.remained_data == True:
            nPrevNext = 2
            # 서버요청
            self.server_set_rq_stock_have_data(sID1, sValue1, sID2, sValue2, sID3, sValue3, sID4, sValue4, sRQName, sTrCode,
                                           nPrevNext, sScreenNo)

    # 체결강도조회 - 이벤트 슬롯 - 관심종목 조회함수 활용
    def deal_power_trans_fn(self, transCode, transCode_cnt):
        # 체결강도조회
        sArrCode = transCode
        bNext = "0"
        nCodeCount = transCode_cnt
        nTypeFlag = 0
        sRQName = "체결강도조회"
        sScreenNo = "0130"
        # 서버요청
        self.printt('# 체결강도조회 전송')
        self.comm_kw_rq_data(sArrCode, bNext, nCodeCount, nTypeFlag, sRQName, sScreenNo)

    # 선물월차트요청
    def future_s_shlc_month_data_fn(self, future_s_code, current_today):
        # 선물월차트요청
        sID1 = "종목코드"
        sValue1 = future_s_code
        sID2 = "기준일자"
        sValue2 = current_today
        sRQName = "선물월차트요청"
        sTrCode = "opt50072"
        nPrevNext = "0"
        sScreenNo = "50072"
        # 서버요청
        self.printt('# 선물월차트요청 전송')
        self.server_set_rq_future_s_shlc_month_data(sID1, sValue1, sID2, sValue2, sRQName,
                                                 sTrCode, nPrevNext, sScreenNo)

    # 선물일차트요청
    def future_s_shlc_day_data_fn(self, future_s_code, current_today):
        # 선물일차트요청
        sID1 = "종목코드"
        sValue1 = future_s_code
        # sID2 = "기준일자"
        # sValue2 = current_today
        sRQName = "선물일차트요청"
        sTrCode = "OPT50030"
        nPrevNext = "0"
        sScreenNo = "50030"
        # 서버요청
        self.printt('# 선물일차트요청 전송')
        self.server_set_rq_future_s_shlc_day_data(sID1, sValue1, sRQName,
                                                 sTrCode, nPrevNext, sScreenNo)

    # 주식월봉차트조회요청
    def stock_shlc_month_data_fn(self, stock_code, ref_day, end_day):
        # 주식월봉차트조회요청
        sID1 = "종목코드"
        sValue1 = stock_code
        sID2 = "기준일자"
        sValue2 = ref_day
        sID3 = "끝일자"
        sValue3 = end_day
        sID4 = "수정주가구분"
        sValue4 = 0
        sRQName = "주식월봉차트조회요청"
        sTrCode = "opt10083"
        nPrevNext = "0"
        sScreenNo = "10083"
        # 서버요청
        self.printt('# 주식월봉차트조회요청 전송')
        self.server_set_rq_stock_shlc_month_data(sID1, sValue1, sID2, sValue2, sID3, sValue3, sID4, sValue4, sRQName,
                                                 sTrCode, nPrevNext, sScreenNo)

    # 주식일봉차트조회요청
    def stock_shlc_day_data_fn(self, stock_code, current_today):
        # 주식일봉차트조회요청
        sID1 = "종목코드"
        sValue1 = stock_code
        sID2 = "기준일자"
        sValue2 = current_today
        sID3 = "수정주가구분"
        sValue3 = "0"
        sRQName = "주식일봉차트조회요청"
        sTrCode = "opt10081"
        nPrevNext = "0"
        sScreenNo = "10081"
        # 서버요청
        self.printt('# 주식일봉차트조회요청 전송')
        self.server_set_rq_stock_shlc_data(sID1, sValue1, sID2, sValue2, sID3, sValue3, sRQName, sTrCode, nPrevNext, sScreenNo)

    # 선옵잔고요청 변수선언
    # 주문시 선옵잔고 변수 초기화
    def reset_myhave_var(self):
        self.option_myhave = {'code': [], 'myhave_cnt': [], 'sell_or_buy': []}

    # 선옵잔고요청 - 이벤트 슬롯
    def myhave_option_rq(self):
        # 선옵잔고요청
        sID = "계좌번호"
        accountrunVar = self.comboBox_acc.currentText()
        sRQName = "선옵잔고요청"
        sTrCode = "OPT50027"
        nPrevNext = 0
        sScreenNo = "50027"
        # 서버요청
        self.printt('# 선옵잔고요청')
        self.server_set_rq_MyHave(sID, accountrunVar, sRQName, sTrCode, nPrevNext, sScreenNo)

        # -----
        # 예탁금및증거금조회 - 이벤트 슬롯
        self.mymoney_option_rq()
        # 계좌평가잔고내역요청[stock]
        self.stock_have_data_rq()
        # 선옵계좌별주문가능수량요청
        item_code = self.futrue_s_data['item_code'][0]
        sell_or_buy_type = '1'  # 매도 매수 타입 # "매매구분"(1:매도, 2:매수)
        price_type = '1'  # 주문유형 = 1:지정가, 3:시장가
        item_order_price_six_digit = int(self.futrue_s_data['run_price'][0] * 1000)
        # print(item_order_price_six_digit)
        item_order_price_five_digit_str = str(item_order_price_six_digit)
        # print(item_order_price_five_digit_str)
        self.future_s_option_s_order_able_cnt_rq(item_code, sell_or_buy_type, price_type,
                                                 item_order_price_five_digit_str)
        # -----

        # -----
        # 위의 : [선옵잔고요청 / 예탁금및증거금조회 / 계좌평가잔고내역요청 / 선옵계좌별주문가능수량요청] 이후 선옵 잔고확인 버튼 변수 True
        # 선옵 잔고확인 버튼 변수
        self.myhave_option_button_var = True
        # 선옵 잔고확인 클릭 했는지 여부
        self.pushButton_myhave.setStyleSheet('background-color: rgb(0, 255, 0)')
        # -----

    # 예탁금및증거금조회 - 이벤트 슬롯
    def mymoney_option_rq(self):
        # 예탁금및증거금조회
        sID1 = "계좌번호"
        accountrunVar = self.comboBox_acc.currentText()
        sID2 = "비밀번호"
        sValue2 = ''
        sID3 = "비밀번호입력매체구분"
        sValue3 = '00'
        sRQName = "예탁금및증거금조회"
        sTrCode = "OPW20010"
        nPrevNext = '0'
        sScreenNo = "20010"
        # 서버요청
        self.printt('# 예탁금및증거금조회')
        self.server_set_rq_OptionMoney(sID1, accountrunVar, sID2, sValue2, sID3, sValue3, sRQName, sTrCode, nPrevNext, sScreenNo)

    # 선옵계좌별주문가능수량요청 - 이벤트 슬롯
    def future_s_option_s_order_able_cnt_rq(self, item_code, sell_or_buy_type, price_type, item_order_price):
        # 선옵계좌별주문가능수량요청
        sID1 = "계좌번호"
        accountrunVar = self.comboBox_acc.currentText()
        sID2 = "비밀번호"
        sValue2 = ''
        sID3 = "종목코드"
        sValue3 = item_code
        sID4 = "매도수구분"
        sValue4 = sell_or_buy_type
        sID5 = "주문유형"
        sValue5 = price_type
        sID6 = "주문가격"
        sValue6 = item_order_price
        sID7 = "비밀번호입력매체구분"
        sValue7 = '00'
        sRQName = "선옵계좌별주문가능수량요청"
        sTrCode = "opw20009"
        nPrevNext = '0'
        sScreenNo = "20009"
        # 서버요청
        self.printt('# 선옵계좌별주문가능수량요청')
        self.server_set_rq_future_s_option_s_order_able_cnt(sID1, accountrunVar, sID2, sValue2, sID3, sValue3,
                                                            sID4, sValue4, sID5, sValue5, sID6, sValue6, sID7, sValue7,
                                                            sRQName, sTrCode, nPrevNext, sScreenNo)

    # 테스트
    def test(self):
        # -----
        # 시간표시
        current_time = datetime.datetime.now()
        current_year = datetime.datetime.today().strftime("%Y")
        current_today = datetime.datetime.today().strftime("%Y%m%d")
        # print(current_time)
        # print(current_time.time())
        # index_text_time = current_time.toString('hh:mm')
        store_time_var = current_time.time()
        # current_time = time.ctime()
        # -----

        # =====
        # # -----
        # self.item_list_cnt_type = {'code_no': ['101V3000', '101V6000', '201V2352', '201V2360'], 'cnt': [5, 2, 4, 10],
        #                            'sell_buy_type': [2, 1, 2, 1], 'state': [0, 0, 0, 0], 'order_no': [1, 2, 1, 2]}

        # self.option_myhave = {'code': ['101V3000', '101V6000'], 'myhave_cnt': [2, 2], 'sell_or_buy': [2, 2]}
        # =====


    # 장마감 c_to_cf_hand <= 변경해서 실시간 db만 저장하는것으로
    def c_to_cf_realtime(self):
        # 장마감 c 이후 <= 20240123 이후 부터 장시작시와 마감시에 2회 실행하기로 함
        # db_store 폴더
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        is_db_file = os.path.isdir(db_file_path)
        if is_db_file == False:
            os.makedirs(db_file_path)
        # txt_store 폴더
        txt_file_path = os.getcwd() + '/' + Folder_Name_TXT_Store
        is_txt_file = os.path.isdir(txt_file_path)
        if is_txt_file == False:
            os.makedirs(txt_file_path)

        # API에서 지난 월봉(30개월)간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
        # API에서 지난 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
        current_year = datetime.datetime.today().strftime("%Y")
        current_today = datetime.datetime.today().strftime("%Y%m%d")

        # (실시간)stock_shlc db저장은 3: 장시작 이후에만 :: 시고저종의 데이타가 0인것이 있음
        # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        if self.MarketEndingVar == '3':
            # 텍스트파일명용
            choice_stock_filename = 'favorites_item_list'
            # db명 설정(월봉 / 일봉)
            db_name_db_month = Folder_Name_DB_Store + '/' + '/' + 'favorites_stock_shlc_data_month' + '.db'
            db_name_db_day = Folder_Name_DB_Store + '/' + '/' + 'favorites_stock_shlc_data_day' + '.db'
            # print(db_name_db_month)
            # print(db_name_db_day)
            self.stock_shlc_store_for_ai_realtime_fn(current_today, choice_stock_filename, db_name_db_month, db_name_db_day)

        # 연결선물
        choice_chain_future_s_item_code = Chain_Future_s_Item_Code
        # db명 설정(월봉 / 일봉)
        db_name_db_month = Folder_Name_DB_Store + '/' + '/' + 'future_s_shlc_data_month' + '.db'
        db_name_db_day = Folder_Name_DB_Store + '/' + '/' + 'future_s_shlc_data_day' + '.db'
        # print(db_name_db_month)
        # print(db_name_db_day)
        self.future_s_store_for_ai_realtime_fn(current_today, choice_chain_future_s_item_code, db_name_db_month,
                                      db_name_db_day)

        # -----
        # AI trend_line
        # 일봉
        # 관리종목
        # db명 설정
        get_db_name = 'favorites_stock_shlc_data_day' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_day' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 20
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
        # 연결선물
        # db명 설정
        get_db_name = 'future_s_shlc_data_day' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_day' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 20
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
        # 관리종목
        # db명 설정
        get_db_name = 'favorites_stock_shlc_data_day' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_day' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 60
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
        # 연결선물
        # db명 설정
        get_db_name = 'future_s_shlc_data_day' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_day' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 60
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
        # -----

    # 장마감 c_to_cf_hand
    def c_to_cf_hand(self):
        # 장마감 c 이후 <= 20240123 이후 부터 장시작시와 마감시에 2회 실행하기로 함
        # db_store 폴더
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        is_db_file = os.path.isdir(db_file_path)
        if is_db_file == False:
            os.makedirs(db_file_path)
        # txt_store 폴더
        txt_file_path = os.getcwd() + '/' + Folder_Name_TXT_Store
        is_txt_file = os.path.isdir(txt_file_path)
        if is_txt_file == False:
            os.makedirs(txt_file_path)

        # API에서 지난 월봉(30개월)간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
        # API에서 지난 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
        current_year = datetime.datetime.today().strftime("%Y")
        current_today = datetime.datetime.today().strftime("%Y%m%d")

        # 텍스트파일명용
        choice_stock_filename = 'favorites_item_list'
        # db명 설정(월봉 / 일봉)
        db_name_db_month = Folder_Name_DB_Store + '/' + '/' + 'favorites_stock_shlc_data_month' + '.db'
        db_name_db_day = Folder_Name_DB_Store + '/' + '/' + 'favorites_stock_shlc_data_day' + '.db'
        # print(db_name_db_month)
        # print(db_name_db_day)
        self.stock_shlc_store_for_ai_fn(current_today, choice_stock_filename, db_name_db_month, db_name_db_day)

        # 연결선물
        choice_chain_future_s_item_code = Chain_Future_s_Item_Code
        # db명 설정(월봉 / 일봉)
        db_name_db_month = Folder_Name_DB_Store + '/' + '/' + 'future_s_shlc_data_month' + '.db'
        db_name_db_day = Folder_Name_DB_Store + '/' + '/' + 'future_s_shlc_data_day' + '.db'
        # print(db_name_db_month)
        # print(db_name_db_day)
        self.future_s_store_for_ai_fn(current_today, choice_chain_future_s_item_code, db_name_db_month,
                                      db_name_db_day)

        # -----
        # trend_line 저장(장마감 이후만)
        if self.MarketEndingVar == 'c':
            # AI trend_line
            db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
            # 월봉
            # 관리종목
            # db명 설정
            get_db_name = 'favorites_stock_shlc_data_month' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_month' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 30
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
            # 연결선물
            # db명 설정
            get_db_name = 'future_s_shlc_data_month' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_month' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 30
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

            # 일봉
            # 관리종목
            # db명 설정
            get_db_name = 'favorites_stock_shlc_data_day' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_day' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 20
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
            # 연결선물
            # db명 설정
            get_db_name = 'future_s_shlc_data_day' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_day' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 20
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
            # 관리종목
            # db명 설정
            get_db_name = 'favorites_stock_shlc_data_day' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_day' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 60
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
            # 연결선물
            # db명 설정
            get_db_name = 'future_s_shlc_data_day' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_day' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 60
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)
        # -----

        # -----
        # 시뮬레이션 실행(장마감 이후만)
        if self.MarketEndingVar == 'c':
            # 일봉 시뮬레이션
            stock_price_candle_cnt = [20, 60]
            for day in stock_price_candle_cnt:
                # print(day)
                # 일봉 시뮬레이션 저장
                # db명 설정
                get_db_name = 'future_s_shlc_data_day' + '.db'
                # db명 설정
                put_db_name = 'future_s_simul_of_trend_line_' + str(day) + 'd' + '.db'
                # 봉갯수
                # stock_price_candle_cnt = 60
                future_s_simul_of_trend_line_store_2060(current_today, db_file_path, get_db_name, put_db_name, day)
            for day in stock_price_candle_cnt:
                # print(day)
                # 일봉 시뮬레이션 저장
                # db명 설정
                get_db_name = 'future_s_shlc_data_day' + '.db'
                # db명 설정
                put_db_name = 'future_s_simul_of_trend_line_' + str(day + 1) + 'd' + '.db'
                # 봉갯수
                # stock_price_candle_cnt = 60
                future_s_simul_of_trend_line_store_2161(current_today, db_file_path, get_db_name, put_db_name, day)

            # 선택종목 crawling 이후 장마감 변수 클리어
            self.MarketEndingVar = 'cf'
            self.printt('self.MarketEndingVar = cf')
            # 시간표시
            current_time = time.ctime()
            self.printt(current_time)
        # -----

    # -----
    # QRadioButton
    def radioButton_20_fn(self):
        # 레디오버튼에 새겨진 택스트 가져오기
        stock_price_candle_str = self.radioButton_20.text()
        # 봉갯수
        self.stock_price_candle_cnt = int(stock_price_candle_str)
        # 일자 콤보박스 내용살피고
        select_combobox_code = self.comboBox_code_s_day.currentText()
        select_combobox_date = self.comboBox_date_s_day.currentText()
        if select_combobox_code == '':
            # 만약에 공백이면 우선 코드 채우면 날자도 채워짐
            self.data_pickup_code_s_day_select_fill()
        elif select_combobox_date == '':
            # 만약에 공백이면 우선 날자 채우고
            self.data_pickup_date_s_day_select_fill()
        # 일봉(차트그리기)
        self.data_pickup_chart_s_day()
    def radioButton_60_fn(self):
        # 레디오버튼에 새겨진 택스트 가져오기
        stock_price_candle_str = self.radioButton_60.text()
        # 봉갯수
        self.stock_price_candle_cnt = int(stock_price_candle_str)
        # 일자 콤보박스 내용살피고
        select_combobox_code = self.comboBox_code_s_day.currentText()
        select_combobox_date = self.comboBox_date_s_day.currentText()
        if select_combobox_code == '':
            # 만약에 공백이면 우선 코드 채우면 날자도 채워짐
            self.data_pickup_code_s_day_select_fill()
        elif select_combobox_date == '':
            # 만약에 공백이면 우선 날자 채우고
            self.data_pickup_date_s_day_select_fill()
        # 일봉(차트그리기)
        self.data_pickup_chart_s_day()
    def radioButton_30_fn(self):
        # 레디오버튼에 새겨진 택스트 가져오기
        stock_price_candle_str = self.radioButton_30.text()
        # 봉갯수
        self.stock_price_candle_cnt = int(stock_price_candle_str)
        # 일자 콤보박스 내용살피고
        select_combobox_code = self.comboBox_code_s_day.currentText()
        select_combobox_date = self.comboBox_date_s_day.currentText()
        if select_combobox_code == '':
            # 만약에 공백이면 우선 코드 채우면 날자도 채워짐
            self.data_pickup_code_s_day_select_fill()
        elif select_combobox_date == '':
            # 만약에 공백이면 우선 날자 채우고
            self.data_pickup_date_s_day_select_fill()
        # 일봉(차트그리기)
        self.data_pickup_chart_s_day()
    def radioButton_40_fn(self):
        # 레디오버튼에 새겨진 택스트 가져오기
        stock_price_candle_str = self.radioButton_40.text()
        # 봉갯수
        self.stock_price_candle_cnt = int(stock_price_candle_str)
        # 일자 콤보박스 내용살피고
        select_combobox_code = self.comboBox_code_s_day.currentText()
        select_combobox_date = self.comboBox_date_s_day.currentText()
        if select_combobox_code == '':
            # 만약에 공백이면 우선 코드 채우면 날자도 채워짐
            self.data_pickup_code_s_day_select_fill()
        elif select_combobox_date == '':
            # 만약에 공백이면 우선 날자 채우고
            self.data_pickup_date_s_day_select_fill()
        # 일봉(차트그리기)
        self.data_pickup_chart_s_day()
    def checkbox_today_x_statechanged(self):
        # checkbox_today_x 상태가 변할 때 마다
        # 일자 콤보박스 내용살피고
        select_combobox_code = self.comboBox_code_s_day.currentText()
        select_combobox_date = self.comboBox_date_s_day.currentText()
        if select_combobox_code == '':
            # 만약에 공백이면 우선 코드 채우면 날자도 채워짐
            self.data_pickup_code_s_day_select_fill()
        elif select_combobox_date == '':
            # 만약에 공백이면 우선 날자 채우고
            self.data_pickup_date_s_day_select_fill()
        # 일봉(차트그리기)
        self.data_pickup_chart_s_day()
    # -----

    # 장시작 3 - 이벤트 슬롯
    def market_start_3(self):
        # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        self.MarketEndingVar = '3'
        self.printt('# self.MarketEndingVar - Hand')
        self.printt(self.MarketEndingVar)
        # 시간표시
        current_time = time.ctime()
        self.printt(current_time)

    # 장마감 c - 이벤트 슬롯
    def market_ending_c(self):
        # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        self.MarketEndingVar = 'c'
        self.printt('# self.MarketEndingVar - Hand')
        self.printt(self.MarketEndingVar)
        # 시간표시
        current_time = time.ctime()
        self.printt(current_time)

    # 자동주문 클릭시 - 이벤트 슬롯
    def auto_order_button(self):
        if self.auto_order_button_var == False:
            # 선옵잔고요청 - 이벤트 슬롯
            self.myhave_option_rq()

            # -----
            self.pushButton_auto_order.setStyleSheet('background-color: rgb(255, 255, 0)')
            # 계좌선택 못하게
            self.comboBox_acc.setEnabled(False)
            self.comboBox_acc_stock.setEnabled(False)
            # 선옵잔고요청 및 예탁금및증거금조회 / 계좌평가잔고내역요청[stock] / 선옵계좌별주문가능수량요청
            # 모두 완료 된 이후 자동주문 self.auto_order_button_var = True
            self.auto_order_button_var = True
            self.printt('# self.auto_order_button_var')
            self.printt(self.auto_order_button_var)
            # -----

        elif self.auto_order_button_var == True:
            self.auto_order_button_var = False
            self.printt(self.auto_order_button_var)
            self.pushButton_auto_order.setStyleSheet('background-color: rgb(255, 255, 255)')
            # 계좌선택 다시 가능
            self.comboBox_acc.setEnabled(True)
            self.comboBox_acc_stock.setEnabled(True)

# 실시간
    # 실시간 이벤트 발생후 처리
    def _receive_real_data(self, strCode, sRealType, sRealData):
        # 실시간 이벤트 처리 가능여부 변수
        if self.receive_real_data_is_OK == True:
        # # QTimer의 상태반환
        # # QTimer가 작동중인지 체크. 작동중이면 True, 멈춰있으면 False
        # if self.timer1.isActive() == True:
            if (self.center_index != 0) and (self.center_index_45 != 0):

                if sRealType == "선물시세":
                    self._real_time_future_s_price(strCode, sRealType)
                elif sRealType == "옵션시세":
                    self._real_time_option_price(strCode, sRealType)
                elif sRealType == "옵션호가잔량":
                    self._real_time_option_price_cnt(strCode, sRealType)

                elif sRealType == "주식시세":
                    self._real_time_stock_price(strCode, sRealType)
                elif sRealType == "주식체결":
                    self._real_time_stock_deal_ok(strCode, sRealType)
                elif sRealType == "주식우선호가":
                    self._real_time_stock_price_sellbuy(strCode, sRealType)
                elif sRealType == "주식호가잔량":
                    self._real_time_stock_price_cnt(strCode, sRealType)

                elif sRealType == "장시작시간":
                    self._real_time_endding_market(strCode, sRealType)

    # 실시간 수신 API 함수 처리
    # if (sRealType == "선물시세"):
    def _real_time_future_s_price(self, strCode, sRealType):
        run_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 10)
        sell_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 27)
        buy_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 28)
        vol_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 13)
        start_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 16)
        high_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 17)
        low_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 18)
        theorist_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 182)
        market_basis = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 183)
        theorist_basis = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 184)

        if strCode == self.futrue_s_data['item_code'][0]:
            # 선물시세
            self.futrue_s_data['run_price'][0] = (abs(float(run_price)))
            self.futrue_s_data['sell_price'][0] = (abs(float(sell_price)))
            self.futrue_s_data['buy_price'][0] = (abs(float(buy_price)))
            self.futrue_s_data['vol_cnt'][0] = (abs(int(vol_cnt)))
            self.futrue_s_data['start_price'][0] = (abs(float(start_price)))
            self.futrue_s_data['high_price'][0] = (abs(float(high_price)))
            self.futrue_s_data['low_price'][0] = (abs(float(low_price)))
            self.futrue_s_data['theorist_price'][0] = (abs(float(theorist_price)))
            self.futrue_s_data['market_basis'][0] = (abs(float(market_basis)))
            self.futrue_s_data['theorist_basis'][0] = (abs(float(theorist_basis)))

        if strCode == self.futrue_s_data_45['item_code'][0]:
            # 선물시세_차월물
            self.futrue_s_data_45['run_price'][0] = (abs(float(run_price)))
            self.futrue_s_data_45['sell_price'][0] = (abs(float(sell_price)))
            self.futrue_s_data_45['buy_price'][0] = (abs(float(buy_price)))
            self.futrue_s_data_45['vol_cnt'][0] = (abs(int(vol_cnt)))
            self.futrue_s_data_45['start_price'][0] = (abs(float(start_price)))
            self.futrue_s_data_45['high_price'][0] = (abs(float(high_price)))
            self.futrue_s_data_45['low_price'][0] = (abs(float(low_price)))
            self.futrue_s_data_45['theorist_price'][0] = (abs(float(theorist_price)))
            self.futrue_s_data_45['market_basis'][0] = (abs(float(market_basis)))
            self.futrue_s_data_45['theorist_basis'][0] = (abs(float(theorist_basis)))

    # if (sRealType == "옵션시세"):
    def _real_time_option_price(self, strCode, sRealType):
        # (KOSPI200 - 197, 선물최근월물지수 - 219)
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        run_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 10)
        sell_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 27)
        buy_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 28)
        vol_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 13)
        future_s = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 219)
        k200_s = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 197)

        Delta = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 190)
        Gamma = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 191)
        Theta = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 193)
        Vega = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 192)
        Rho = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 194)

        # 최상단과 최하단의 매수도호가는 공백임
        if (sell_price == '') or (buy_price == ''):
            sell_price = 0
            buy_price = 0

        for i in range(self.center_index - Up_CenterOption_Down, self.center_index + Up_CenterOption_Down + 1):
            # (콜(최근)종목결제월별시세요청)
            self.output_call_option_data['future_s'][i] = self.futrue_s_data['run_price'][0]
            self.output_call_option_data['k200_s'][i] = (abs(float(k200_s)))
            # (풋(최근)종목결제월별시세요청)
            self.output_put_option_data['future_s'][i] = self.futrue_s_data['run_price'][0]
            self.output_put_option_data['k200_s'][i] = (abs(float(k200_s)))
            if strCode == self.output_call_option_data['code'][i]:
                # (콜(최근)종목결제월별시세요청)
                # # 현재가 저장은 매도호가 보다 작고 매수호가 보다 클때 만
                # if self.output_call_option_data['sell_price'][i] >= (abs(float(run_price))):
                #     if (abs(float(run_price))) >= self.output_call_option_data['buy_price'][i]:
                self.output_call_option_data['run_price'][i] = (abs(float(run_price)))
                self.output_call_option_data['sell_price'][i] = (abs(float(sell_price)))
                self.output_call_option_data['buy_price'][i] = (abs(float(buy_price)))
                self.output_call_option_data['vol_cnt'][i] = (abs(int(vol_cnt)))

                self.output_call_option_data['Delta'][i] = (abs(float(Delta)))
                self.output_call_option_data['Gamma'][i] = (abs(float(Gamma)))
                self.output_call_option_data['Theta'][i] = (abs(float(Theta)))
                self.output_call_option_data['Vega'][i] = (abs(float(Vega)))
                self.output_call_option_data['Rho'][i] = (abs(float(Rho)))

            if strCode == self.output_put_option_data['code'][i]:
                # (풋(최근)종목결제월별시세요청)
                # # 현재가 저장은 매도호가 보다 작고 매수호가 보다 클때 만
                # if self.output_put_option_data['sell_price'][i] >= (abs(float(run_price))):
                #     if (abs(float(run_price))) >= self.output_put_option_data['buy_price'][i]:
                self.output_put_option_data['run_price'][i] = (abs(float(run_price)))
                self.output_put_option_data['sell_price'][i] = (abs(float(sell_price)))
                self.output_put_option_data['buy_price'][i] = (abs(float(buy_price)))
                self.output_put_option_data['vol_cnt'][i] = (abs(int(vol_cnt)))

                self.output_put_option_data['Delta'][i] = (abs(float(Delta)))
                self.output_put_option_data['Gamma'][i] = (abs(float(Gamma)))
                self.output_put_option_data['Theta'][i] = (abs(float(Theta)))
                self.output_put_option_data['Vega'][i] = (abs(float(Vega)))
                self.output_put_option_data['Rho'][i] = (abs(float(Rho)))

        # 차월물
        for i in range(self.center_index_45 - Up_CenterOption_Down, self.center_index_45 + Up_CenterOption_Down + 1):
            # 콜종목결제월별시세요청_45
            self.output_call_option_data_45['future_s'][i] = self.futrue_s_data['run_price'][0]
            self.output_call_option_data_45['k200_s'][i] = (abs(float(k200_s)))
            # 풋종목결제월별시세요청_45
            self.output_put_option_data_45['future_s'][i] = self.futrue_s_data['run_price'][0]
            self.output_put_option_data_45['k200_s'][i] = (abs(float(k200_s)))
            if strCode == self.output_call_option_data_45['code'][i]:
                # 콜종목결제월별시세요청_45
                self.output_call_option_data_45['run_price'][i] = (abs(float(run_price)))
                self.output_call_option_data_45['sell_price'][i] = (abs(float(sell_price)))
                self.output_call_option_data_45['buy_price'][i] = (abs(float(buy_price)))
                self.output_call_option_data_45['vol_cnt'][i] = (abs(int(vol_cnt)))

                self.output_call_option_data_45['Delta'][i] = (abs(float(Delta)))
                self.output_call_option_data_45['Gamma'][i] = (abs(float(Gamma)))
                self.output_call_option_data_45['Theta'][i] = (abs(float(Theta)))
                self.output_call_option_data_45['Vega'][i] = (abs(float(Vega)))
                self.output_call_option_data_45['Rho'][i] = (abs(float(Rho)))

            if strCode == self.output_put_option_data_45['code'][i]:
                # 풋종목결제월별시세요청_45
                self.output_put_option_data_45['run_price'][i] = (abs(float(run_price)))
                self.output_put_option_data_45['sell_price'][i] = (abs(float(sell_price)))
                self.output_put_option_data_45['buy_price'][i] = (abs(float(buy_price)))
                self.output_put_option_data_45['vol_cnt'][i] = (abs(int(vol_cnt)))

                self.output_put_option_data_45['Delta'][i] = (abs(float(Delta)))
                self.output_put_option_data_45['Gamma'][i] = (abs(float(Gamma)))
                self.output_put_option_data_45['Theta'][i] = (abs(float(Theta)))
                self.output_put_option_data_45['Vega'][i] = (abs(float(Vega)))
                self.output_put_option_data_45['Rho'][i] = (abs(float(Rho)))

    # elif (sRealType == "옵션호가잔량"):
    def _real_time_option_price_cnt(self, strCode, sRealType):
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        sell_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 27)
        sell_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 61)
        buy_price = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 28)
        buy_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 71)

        # 최상단과 최하단의 매수도호가는 공백임
        if (sell_price == '') or (buy_price == ''):
            sell_price = 0
            buy_price = 0

        for i in range(self.center_index - Up_CenterOption_Down, self.center_index + Up_CenterOption_Down + 1):
            if strCode == self.output_call_option_data['code'][i]:
                # (콜(최근)종목결제월별시세요청)
                self.output_call_option_data['sell_price'][i] = (abs(float(sell_price)))
                self.output_call_option_data['sell_cnt'][i] = (abs(int(sell_cnt)))
                self.output_call_option_data['buy_price'][i] = (abs(float(buy_price)))
                self.output_call_option_data['buy_cnt'][i] = (abs(int(buy_cnt)))
            elif strCode == self.output_put_option_data['code'][i]:
                # (풋(최근)종목결제월별시세요청)
                self.output_put_option_data['sell_price'][i] = (abs(float(sell_price)))
                self.output_put_option_data['sell_cnt'][i] = (abs(int(sell_cnt)))
                self.output_put_option_data['buy_price'][i] = (abs(float(buy_price)))
                self.output_put_option_data['buy_cnt'][i] = (abs(int(buy_cnt)))

        # 차월물
        for i in range(self.center_index_45 - Up_CenterOption_Down, self.center_index_45 + Up_CenterOption_Down + 1):
            if strCode == self.output_call_option_data_45['code'][i]:
                # 콜종목결제월별시세요청_45
                self.output_call_option_data_45['sell_price'][i] = (abs(float(sell_price)))
                self.output_call_option_data_45['sell_cnt'][i] = (abs(int(sell_cnt)))
                self.output_call_option_data_45['buy_price'][i] = (abs(float(buy_price)))
                self.output_call_option_data_45['buy_cnt'][i] = (abs(int(buy_cnt)))
            elif strCode == self.output_put_option_data_45['code'][i]:
                # 풋종목결제월별시세요청_45
                self.output_put_option_data_45['sell_price'][i] = (abs(float(sell_price)))
                self.output_put_option_data_45['sell_cnt'][i] = (abs(int(sell_cnt)))
                self.output_put_option_data_45['buy_price'][i] = (abs(float(buy_price)))
                self.output_put_option_data_45['buy_cnt'][i] = (abs(int(buy_cnt)))

        # 실시간 카운터
        self.real_time_total_cnt += 1

    # 주식시세
    def _real_time_stock_price(self, strCode, sRealType):
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        run_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 10)
        stock_start = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 16)
        stock_high = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 17)
        stock_low = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 18)
        stock_end = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 10)
        vol_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 13)

        # print(sRealType)
        # print(strCode)
        # print(run_price)

        # 주식일봉차트조회요청 => c_to_cf_hand 전용(실시간 처리)
        for i in range(len(self.stock_item_data['stock_item_no'])):
            if strCode == self.stock_item_data['stock_item_no'][i]:
                self.stock_item_data['stock_start'][i] = (abs(int(stock_start)))
                self.stock_item_data['stock_high'][i] = (abs(int(stock_high)))
                self.stock_item_data['stock_low'][i] = (abs(int(stock_low)))
                self.stock_item_data['stock_end'][i] = (abs(int(stock_end)))
                self.stock_item_data['vol_cnt'][i] = (abs(int(vol_cnt)))

        for i in range(len(self.stock_have_data['stock_no'])):
            if strCode == self.stock_have_data['stock_no'][i]:
                self.stock_have_data['run_price'][i] = (abs(int(run_price)))

    # 주식체결
    def _real_time_stock_deal_ok(self, strCode, sRealType):
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        run_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 10)
        stock_start = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 16)
        stock_high = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 17)
        stock_low = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 18)
        stock_end = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 10)
        vol_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 13)

        # 주식일봉차트조회요청 => c_to_cf_hand 전용(실시간 처리)
        for i in range(len(self.stock_item_data['stock_item_no'])):
            if strCode == self.stock_item_data['stock_item_no'][i]:
                self.stock_item_data['stock_start'][i] = (abs(int(stock_start)))
                self.stock_item_data['stock_high'][i] = (abs(int(stock_high)))
                self.stock_item_data['stock_low'][i] = (abs(int(stock_low)))
                self.stock_item_data['stock_end'][i] = (abs(int(stock_end)))
                self.stock_item_data['vol_cnt'][i] = (abs(int(vol_cnt)))

        for i in range(len(self.stock_have_data['stock_no'])):
            if strCode == self.stock_have_data['stock_no'][i]:
                self.stock_have_data['run_price'][i] = (abs(int(run_price)))

        if strCode in self.stock_have_data['stock_no']:
            # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
            if self.MarketEndingVar == '3':
                # 선물 변화 건수 체크
                future_s_change_cnt = len(self.future_s_change_listed_var)
                if future_s_change_cnt >= 1:
                    # 선물변화 프로세스 실행중 여부
                    if self.future_s_change_running == False:
                        # 자동주문 버튼 True 주문실행
                        if self.auto_order_button_var == True:
                            # 주식매도 종목검색
                            self.stock_sell_items_search(strCode)

    # 주식우선호가
    def _real_time_stock_price_sellbuy(self, strCode, sRealType):
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        sell_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 27)
        buy_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 28)

        # print(sRealType)
        # print(strCode)
        # print(sell_price)
        # print(buy_price)

    # 주식호가잔량
    def _real_time_stock_price_cnt(self, strCode, sRealType):
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        sell_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 61)
        buy_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 71)

    # elif (sRealType == "장시작시간"):
    def _real_time_endding_market(self, strCode, sRealType):
        self.MarketEndingVar = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 215)

        # 텍스트로 처리함
        # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        # 08:40:01 ~(1분간격)~ 08:59:01 ~(10초간격) 08:59:51
        if self.MarketEndingVar == '0':
            # self.printt(self.MarketEndingVar)
            # self.printt('0:장시작전')
            # # 시간표시
            # current_time = time.ctime()
            # self.printt(current_time)
            pass
        # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        # 15:20:01 ~(1분간격)~ 15:29:00 ~(10초간격)~ 15:29:50
        elif self.MarketEndingVar == '2':
            # self.printt(self.MarketEndingVar)
            # self.printt('2: 장종료전')
            # # 시간표시
            # current_time = time.ctime()
            # self.printt(current_time)
            pass

        # 09:00:01
        elif self.MarketEndingVar == '3':
            self.printt(self.MarketEndingVar)
            self.printt('3: 장시작')
            # 시간표시
            current_time = time.ctime()
            self.printt(current_time)
            # # 콜/풋 월별시세요청 전 - 1초 타이머 중지
            # self.timer1.stop()
            # self.printt('timer1 콜/풋 월별시세요청 전 타이머 중지')
            # # 콜/풋 월별시세요청
            # self.printt('장시작 콜/풋 월별시세요청')
            # self.call_put_data_rq()
            # if self.center_index != 0:
            #     # 비교변수 초기 바인딩(slow)
            #     self.slow_cmp_var_reset()
            # # 주문 실행 결과
            # # 인스턴스 변수 선언
            # self.reset_order_var()
            # # 주문 실행 결과
            # # 인스턴스 변수 선언
            # self.reset_order_var_stock()

        # elif self.MarketEndingVar == 'e':
        #     self.printt(self.MarketEndingVar)
        #     self.printt('장마감 e')    # 15:45:01(반복)
        #     # 시간표시
        #     current_time = time.ctime()
        #     self.printt(current_time)

        # 16:00:00
        elif self.MarketEndingVar == 'c':
            self.printt(self.MarketEndingVar)
            self.printt('c: 장마감')
            # 시간표시
            current_time = time.ctime()
            self.printt(current_time)

        # elif self.MarketEndingVar == '8':

        # elif self.MarketEndingVar == 'a':

        # elif self.MarketEndingVar == '9':
        #     self.printt(self.MarketEndingVar)
        #     self.printt('장마감 9')    # 18:01:31
        #     # 시간표시
        #     current_time = time.ctime()
        #     self.printt(current_time)
        #     # # 일지정리(장마감 타이머 start())
        #     # # 장마감 타이머 시작
        #     # self.timer_market_edding.start(1000 * 30)
        #     # self.printt('장마감 타이머 시작')


# 주문
    # 체결잔고 데이터를 가져오는 메서드인 GetChejanData를 사용하는 get_chejan_data 메서드를 클래스에 추가
    def get_chejan_data(self, fid):
        ret = self.kiwoom.dynamicCall("GetChejanData(int)", fid)
        return ret.strip()

    #  OnReceiveChejanData 이벤트가 발생할 때 호출되는 _receive_chejan_data는 다음과 같이 구현
    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        # sGubun – 0: 주문체결통보, 1: 국내주식 잔고통보, 4: 파생상품 잔고통보
        # sFidList – 데이터 구분은 ‘;’ 이다

        # # 자동주문 아닐때는(수동 주문일때)는 패스
        # if self.auto_order_button_var == False:
        #     return

        # print(item_cnt)
        # print(fid_list)
        if gubun == '0':
            # print(gubun)
            # 주문상태
            OrderRunKind = self.get_chejan_data(913)
            # 접수
            if OrderRunKind == "접수":
                # 주문상태 / 매수도구분/ 종목코드 / 주문수량 / 주문가격 / 원 주문번호
                SellBuyType = self.get_chejan_data(907)
                OrderRunCode = self.get_chejan_data(9001)
                OrderRunCode_A = self.get_chejan_data(9001)
                OrderRunVolume = self.get_chejan_data(900)
                OrderRunPrice = self.get_chejan_data(901)
                OrgOrderNo = self.get_chejan_data(9203)

                # -----
                # 초단위 주문변수 수정   # 접수
                code = self.get_chejan_data(9001)   # "종목코드"
                order_cnt = abs(int(self.get_chejan_data(900)))     # "주문수량"
                order_sell_or_buy = abs(int(self.get_chejan_data(907)))     # "매도수구분"
                order_no = abs(int(self.get_chejan_data(9203)))   # "주문번호"
                # 종목코드 주문변수 있고 없고
                if code in self.item_list_cnt_type['code_no']:
                    # 초단위 주문변수 종목코드 기준으로 돌리면서
                    for i in range(len(self.item_list_cnt_type['code_no'])):
                        # 종목코드 같고
                        if self.item_list_cnt_type['code_no'][i] == code:
                            # 매도수구분 같으면
                            if self.item_list_cnt_type['sell_buy_type'][i] == order_sell_or_buy:
                                # 주문수량 같으면    [1건씩 주문하므로 확인 불필요 20240208]
                                if self.order_cnt_onetime == order_cnt:
                                    # 1(주문) 확인
                                    if self.item_list_cnt_type['state'][i] == 1:
                                        # 주문변수 주문번호 변경하고
                                        self.item_list_cnt_type['order_no'][i] = order_no
                    # 시간표시
                    current_time = time.ctime()
                    self.printt(current_time)
                    self.printt('self.item_list_cnt_type - # 접수')
                    self.printt(self.item_list_cnt_type)
                # -----



                # option 자릿수 8
                if len(OrderRunCode) == 8:
                    # option
                    order_run_result_var = []
                    order_run_result_var.append(OrderRunKind)
                    order_run_result_var.append(abs(int(SellBuyType)))
                    order_run_result_var.append(OrderRunCode)
                    order_run_result_var.append(abs(int(OrderRunVolume)))
                    order_run_result_var.append(abs(float(OrderRunPrice)))
                    order_run_result_var.append(OrgOrderNo)

                    # # 주문 실행 결과로
                    # self.order_run_result(order_run_result_var)

                else:
                    # stock
                    order_run_result_var = []
                    order_run_result_var.append(OrderRunKind)
                    order_run_result_var.append(abs(int(SellBuyType)))
                    # 종목코드 앞에 A 제거
                    OrderRunCode = OrderRunCode_A[-6:]
                    order_run_result_var.append(OrderRunCode)
                    order_run_result_var.append(abs(int(OrderRunVolume)))
                    order_run_result_var.append(abs(int(OrderRunPrice)))
                    order_run_result_var.append(OrgOrderNo)

                    # # 주문 실행 결과로
                    # self.order_run_result_stock(order_run_result_var)

            # 체결
            elif OrderRunKind == "체결":
                # 주문상태 / 매수도구분/ 종목코드 / 주문수량 / 주문가격 / 원 주문번호
                SellBuyType = self.get_chejan_data(907)
                OrderRunCode = self.get_chejan_data(9001)
                OrderRunCode_A = self.get_chejan_data(9001)
                OrderDealOk_cnt = self.get_chejan_data(911)
                OrderDealOk_price = self.get_chejan_data(910)
                OrgOrderNo = self.get_chejan_data(9203)

                # -----
                # 초단위 주문변수 수정
                code = self.get_chejan_data(9001)   # "종목코드"

                # -----
                deal_ok_cnt = self.get_chejan_data(911)     # "체결량"
                # 문자열을 정수로 바꾸려고 int함수를 사용하였는데,
                # 아래와 같이 ValueError 가 발생
                # ValueError: invalid literal for int() with base 10: ''
                # 20221130 :: 정정 주문 실행 이후 "체결량" '' 공백으로 오는 경우가 있었음(공백은 int,  float 모두 형변환시 에러 발생함)
                if deal_ok_cnt != '':
                    deal_ok_cnt_int = abs(int(deal_ok_cnt))
                elif deal_ok_cnt == '':
                    deal_ok_cnt_int = 0
                # -----

                order_sell_or_buy = abs(int(self.get_chejan_data(907)))     # "매도수구분"
                non_deal_ok_cnt = abs(int(self.get_chejan_data(902)))       # "미체결수량"
                # 종목코드 주문변수 있고 없고
                if code in self.item_list_cnt_type['code_no']:
                    # 초단위 주문변수 종목코드 기준으로 돌리면서
                    for i in range(len(self.item_list_cnt_type['code_no'])):
                        # 종목코드 같고
                        if self.item_list_cnt_type['code_no'][i] == code:
                            # 매도수구분 같으면
                            if self.item_list_cnt_type['sell_buy_type'][i] == order_sell_or_buy:
                                # 1(주문) 확인
                                if self.item_list_cnt_type['state'][i] == 1:
                                    # 주문변수 수량 변경하고
                                    self.item_list_cnt_type['cnt'][i] -= self.order_cnt_onetime
                                    # 20240208 옵션 주문은 1건씩 처리로 변경하면서 다시 self.order_cnt_onetime 만큼 빼주는걸로(방금전까지 미체결 수량으로에서 대체하였었음)
                                    # 시간표시
                                    current_time = time.ctime()
                                    self.printt(current_time)
                                    self.printt('self.item_list_cnt_type[cnt][i] - "self.order_cnt_onetime" 만큼 빼주고')
                                    self.printt(self.item_list_cnt_type['cnt'][i])

                                    # -----
                                    # 방금전 매도였나 매수였나(?)
                                    # 체결량이 0이상일때
                                    if deal_ok_cnt_int > 0:
                                        self.last_order_sell_or_buy = order_sell_or_buy
                                    # -----

                                    # 미체결수량 0이상이면 상태를 0(주문) 변경 :: 다시 주문할수 있도록
                                    # 옵션 주문은 1건씩만 하도록 처리하면서[20240208]
                                    if self.item_list_cnt_type['cnt'][i] > 0:
                                        # 상태를 0(주문) 변경 :: 다시 주문할수 있도록
                                        self.item_list_cnt_type['state'][i] = 0
                                        self.printt('상태를 0(주문) 변경 :: 다시 주문할수 있도록')
                                        # 주문번호도 초기화
                                        self.item_list_cnt_type['order_no'][i] = 0
                                        self.printt('주문번호도 초기화(0)변경 :: 별 상관 없지만')
                                    # 미체결수량 0이하이면 리스트에서 삭제
                                    elif self.item_list_cnt_type['cnt'][i] <= 0:
                                        # 매수/매도종목 텍스트 저장 호출
                                        # 매도 매수 타입 # "매매구분"(1:매도, 2:매수)
                                        if self.item_list_cnt_type['sell_buy_type'][i] == 1:
                                            SellBuyText = '매도'
                                            # 시분초
                                            current_time = QTime.currentTime()
                                            text_time = current_time.toString('hh:mm:ss')
                                            time_msg = ' 체결완료 : ' + text_time
                                            # 텍스트 저장 호출
                                            self.printt_selled(
                                                self.item_list_cnt_type['code_no'][i] + '::(' + SellBuyText + time_msg + ')')
                                        elif self.item_list_cnt_type['sell_buy_type'][i] == 2:
                                            SellBuyText = '매수'
                                            # 시분초
                                            current_time = QTime.currentTime()
                                            text_time = current_time.toString('hh:mm:ss')
                                            time_msg = ' 체결완료 : ' + text_time
                                            # 텍스트 저장 호출
                                            self.printt_buyed(
                                                self.item_list_cnt_type['code_no'][i] + '::(' + SellBuyText + time_msg + ')')
                                        # 리스트에서 삭제
                                        del self.item_list_cnt_type['code_no'][i]
                                        del self.item_list_cnt_type['cnt'][i]
                                        del self.item_list_cnt_type['sell_buy_type'][i]
                                        del self.item_list_cnt_type['state'][i]
                                        del self.item_list_cnt_type['order_no'][i]
                                        self.printt('매수/매도종목 텍스트 저장 및 리스트에서 삭제')
                                        break  # 리스트 요소를 삭제하였으므로 for문 중지(체결과 잔고는 1건씩 올것이므로)
                    # 시간표시
                    current_time = time.ctime()
                    self.printt(current_time)
                    self.printt('self.item_list_cnt_type - "체결"')
                    self.printt(self.item_list_cnt_type)
                # -----

                # 문자열을 정수로 바꾸려고 int함수를 사용하였는데,
                # 아래와 같이 ValueError 가 발생
                # ValueError: invalid literal for int() with base 10: ''
                if OrderDealOk_cnt != '':
                # 20221130 :: 정정 주문 실행 이후 체결정보가 '' 공백으로 오는 경우가 있었음(공백은 int,  float 모두 형변환시 에러 발생함)

                    # option 자릿수 8
                    if len(OrderRunCode) == 8:
                        # option
                        order_run_result_var = []
                        order_run_result_var.append(OrderRunKind)
                        order_run_result_var.append(abs(int(SellBuyType)))
                        order_run_result_var.append(OrderRunCode)
                        order_run_result_var.append(abs(int(OrderDealOk_cnt)))
                        order_run_result_var.append(abs(float(OrderDealOk_price)))
                        order_run_result_var.append(OrgOrderNo)

                        # # 주문 실행 결과로
                        # self.order_run_result(order_run_result_var)

                    else:
                        # stock
                        order_run_result_var = []
                        order_run_result_var.append(OrderRunKind)
                        order_run_result_var.append(abs(int(SellBuyType)))
                        # 종목코드 앞에 A 제거
                        OrderRunCode = OrderRunCode_A[-6:]
                        order_run_result_var.append(OrderRunCode)
                        order_run_result_var.append(abs(int(OrderDealOk_cnt)))
                        order_run_result_var.append(abs(int(OrderDealOk_price)))
                        order_run_result_var.append(OrgOrderNo)

                        # # 주문 실행 결과로
                        # self.order_run_result_stock(order_run_result_var)

            # 확인(취소)
            elif OrderRunKind == "확인":
                # -----
                # 초단위 주문변수 수정   # 확인(취소)
                code = self.get_chejan_data(9001)   # "종목코드"
                order_cnt = abs(int(self.get_chejan_data(900))) # "주문수량"
                order_sell_or_buy = abs(int(self.get_chejan_data(907))) # "매도수구분"
                order_price = abs(float(self.get_chejan_data(901)))   # "주문가격"
                # 종목코드 주문변수 있고 없고
                if code in self.item_list_cnt_type['code_no']:
                    # 초단위 주문변수 종목코드 기준으로 돌리면서
                    for i in range(len(self.item_list_cnt_type['code_no'])):
                        # 종목코드 같고
                        if self.item_list_cnt_type['code_no'][i] == code:
                            # 매도/매수구분 같으면
                            if self.item_list_cnt_type['sell_buy_type'][i] == order_sell_or_buy:
                                # 2(취소) 확인
                                if self.item_list_cnt_type['state'][i] == 2:
                                    # 주문변수 수량 변경하고
                                    # self.item_list_cnt_type['cnt'][i] -= order_cnt
                                    self.item_list_cnt_type['cnt'][i] = 0  # 주문 1건씩 하므로 주문변수 남은수량 0으로
                                    self.printt('self.item_list_cnt_type[''][i] - "확인" 취소 주문변수 변경하고 남은건수')
                                    self.printt(self.item_list_cnt_type['cnt'][i])
                                    # 주문가격 0 확인
                                    if order_price == 0.0:
                                        # 주문변수 건수 0이하이면 리스트에서 삭제
                                        if self.item_list_cnt_type['cnt'][i] <= 0:
                                            del self.item_list_cnt_type['code_no'][i]
                                            del self.item_list_cnt_type['cnt'][i]
                                            del self.item_list_cnt_type['sell_buy_type'][i]
                                            del self.item_list_cnt_type['state'][i]
                                            del self.item_list_cnt_type['order_no'][i]
                                            break  # 리스트 요소를 삭제하였으므로 for문 중지(체결과 잔고는 1건씩 올것이므로)
                    # 시간표시
                    current_time = time.ctime()
                    self.printt(current_time)
                    self.printt('self.item_list_cnt_type - 취소 "확인" 리스트에서 삭제')
                    self.printt(self.item_list_cnt_type)
                # -----

        # gubun – 0: 주문체결통보, 1: 국내주식 잔고통보, 4: 파생상품 잔고통보
        elif gubun == '1':
            # stock
            # stock_data 변수 수정
            code_A = self.get_chejan_data(9001)   # "종목코드"
            # 종목코드 앞에 A 제거
            code = code_A[-6:]
            stock_name = self.get_chejan_data(302)  # "종목명"
            myhave_cnt = abs(int(self.get_chejan_data(930)))    # "보유수량"
            # 종목코드 stock_data 있고 없고
            if code in self.stock_have_data['stock_no']:
                # stock_data 종목코드 기준으로 돌리면서
                for i in range(len(self.stock_have_data['stock_no'])):
                    # 종목코드 같고
                    if self.stock_have_data['stock_no'][i] == code:
                        # 보유수량 변경하고
                        self.stock_have_data['myhave_cnt'][i] = myhave_cnt
                        # 보유수량 0이면 리스트에서 삭제(stock_data 옵션과 다르게 0상태 유지 - 중심가 변경시 재수신)
            # 체결 종목코드가 보유종목에 없을경우는 추가
            elif myhave_cnt > 0:
                self.stock_have_data['stock_no'].append(code)
                self.stock_have_data['stock_name'].append(stock_name)
                self.stock_have_data['market_in_price'].append(abs(int(0)))
                self.stock_have_data['myhave_cnt'].append(myhave_cnt)
                self.stock_have_data['run_price'].append(abs(int(0)))
            # 시간표시
            current_time = time.ctime()
            self.printt(current_time)
            self.printt('# gubun == 1: 국내주식 잔고통보')
            self.printt(len(self.stock_have_data['stock_no']))
            self.printt(self.stock_have_data)

        elif gubun == '4':
            # future_s_option_s
            # 선옵잔고 변수 수정
            code = self.get_chejan_data(9001)   # "종목코드"
            myhave_cnt = abs(int(self.get_chejan_data(930)))    # "보유수량"
            sell_or_buy = abs(int(self.get_chejan_data(946)))   # "매도/매수구분"
            # 종목코드 선옵잔고 있고 없고
            if code in self.option_myhave['code']:
                # 선옵잔고 종목코드 기준으로 돌리면서
                for i in range(len(self.option_myhave['code'])):
                    # 종목코드 같고
                    if self.option_myhave['code'][i] == code:
                        # 매도/매수구분 넣어주고
                        self.option_myhave['sell_or_buy'][i] = sell_or_buy
                        # 보유수량 변경하고
                        self.option_myhave['myhave_cnt'][i] = myhave_cnt
                        # 보유수량 0이면 리스트에서 삭제
                        if self.option_myhave['myhave_cnt'][i] == 0:
                            del self.option_myhave['code'][i]
                            del self.option_myhave['myhave_cnt'][i]
                            del self.option_myhave['sell_or_buy'][i]
                            break   # 리스트 요소를 삭제하였으므로 for문 중지(체결과 잔고는 1건씩 올것이므로)
            # 체결 종목코드가 보유종목에 없을경우는 추가
            elif myhave_cnt > 0:
                self.option_myhave['code'].append(code)
                self.option_myhave['myhave_cnt'].append(myhave_cnt)
                self.option_myhave['sell_or_buy'].append(sell_or_buy)
            # 시간표시
            current_time = time.ctime()
            self.printt(current_time)
            self.printt('# gubun == 4: 파생상품 잔고통보')
            self.printt(self.option_myhave)

        # # -----
        # # 잔고 실시간 처리를 위한 테스트
        # self.printt('# -----')
        # self.printt('# 잔고 실시간 처리를 위한 테스트')
        # self.printt('gubun : ')
        # self.printt(gubun)
        # self.printt('item_cnt : ')
        # self.printt(item_cnt)
        # self.printt('fid_list : ')
        # self.printt(fid_list)
        #
        # self.printt('주문상태 : ')
        # self.printt(self.get_chejan_data(913))
        # self.printt('계좌번호 : ')
        # self.printt(self.get_chejan_data(9201))
        # self.printt('주문번호 : ')
        # self.printt(self.get_chejan_data(9203))
        # self.printt('종목코드 : ')
        # self.printt(self.get_chejan_data(9001))
        # self.printt('종목명 : ')
        # self.printt(self.get_chejan_data(302))
        # self.printt('주문수량 : ')
        # self.printt(self.get_chejan_data(900))
        # self.printt('주문가격 : ')
        # self.printt(self.get_chejan_data(901))
        # self.printt('미체결수량 : ')
        # self.printt(self.get_chejan_data(902))
        # self.printt('원주문번호 : ')
        # self.printt(self.get_chejan_data(904))
        # self.printt('주문구분 : ')
        # self.printt(self.get_chejan_data(905))
        # self.printt('매매구분 : ')
        # self.printt(self.get_chejan_data(906))
        # self.printt('매도수구분 : ')
        # self.printt(self.get_chejan_data(907))
        # self.printt('주문/체결시간 : ')
        # self.printt(self.get_chejan_data(908))
        # self.printt('체결가 : ')
        # self.printt(self.get_chejan_data(910))
        # self.printt('체결량 : ')
        # self.printt(self.get_chejan_data(911))
        # self.printt('거부사유 : ')
        # self.printt(self.get_chejan_data(919))
        # self.printt('화면번호 : ')
        # self.printt(self.get_chejan_data(920))
        # self.printt('주문가능수량 : ')
        # self.printt(self.get_chejan_data(933))
        # self.printt('보유수량 : ')
        # self.printt(self.get_chejan_data(930))
        # self.printt('매도/매수구분 : ')
        # self.printt(self.get_chejan_data(946))
        # self.printt('# -----')
        # # -----

    # 주문테스트
    def order_test(self):
        pass

    # 주문 실행 결과
    # 인스턴스 변수 선언
    def reset_order_var(self):
        # 주문 실행 결과
        self.order_trans_var = {'OrderRunKind': [], 'SellBuyType': [], 'OrderRunCode': [], 'OrderRunVolume': [],
                                 'OrderRunPrice': [], 'OrgOrderNo': [], 'modify_item': []}
        self.order_input_var = {'OrderRunKind': [], 'SellBuyType': [], 'OrderRunCode': [], 'OrderRunVolume': [],
                                 'OrderRunPrice': [], 'OrgOrderNo': [], 'modify_item': []}
        self.order_result_var = {'OrderRunKind': [], 'SellBuyType': [], 'OrderRunCode': [], 'OrderRunVolume': [],
                                 'OrderRunPrice': [], 'OrgOrderNo': [], 'modify_item': []}

    # send_order 메서드에서는 사용자가 위젯을 통해 입력한 정보를 얻어온 후 이를 이용해 Kiwoom 클래스에 구현돼 있는 send_order 메서드를 호출
    def order_ready(self, cross_winner, volume_listed_var, item_list, sOrgOrdNo):
        # 주문 실행 결과
        # 인스턴스 변수 선언
        self.reset_order_var()

        # 주문 종목 인텍스 찾기
        order_index = []
        order_cross_winner = []
        order_volume = []
        order_item = []
        order_sOrgOrdNo = []
        order_23_45 = []

        # 선물
        # 당월물
        for j in range(len(item_list)):
            if item_list[j][:3] == '101':
                if item_list[j] == self.futrue_s_data['item_code'][0]:
                    order_index.append(0)  # int
                    order_cross_winner.append(cross_winner[j])  # int
                    order_volume.append(volume_listed_var[j])  # int
                    order_item.append(item_list[j])
                    order_sOrgOrdNo.append(sOrgOrdNo[j])
                    order_23_45.append(11)  # int
        # 차월물
        for j in range(len(item_list)):
            if item_list[j][:3] == '101':
                if item_list[j] == self.futrue_s_data_45['item_code'][0]:
                    order_index.append(0)  # int
                    order_cross_winner.append(cross_winner[j])  # int
                    order_volume.append(volume_listed_var[j])  # int
                    order_item.append(item_list[j])
                    order_sOrgOrdNo.append(sOrgOrdNo[j])
                    order_23_45.append(22)  # int

        # 콜옵션
        for i in range(self.center_index - Up_CenterOption_Down, self.center_index + Up_CenterOption_Down):
            for j in range(len(item_list)):
                if item_list[j][:3] == '201':
                    if self.output_call_option_data['code'][i] == item_list[j]:
                        order_index.append(i)  # int
                        order_cross_winner.append(cross_winner[j])  # int
                        order_volume.append(volume_listed_var[j])  # int
                        order_item.append(item_list[j])
                        order_sOrgOrdNo.append(sOrgOrdNo[j])
                        order_23_45.append(23)  # int
        # 풋옵션
        for i in range(self.center_index + Up_CenterOption_Down, self.center_index - Up_CenterOption_Down, -1):
            for j in range(len(item_list)):
                if item_list[j][:3] == '301':
                    if self.output_put_option_data['code'][i] == item_list[j]:
                        order_index.append(i)  # int
                        order_cross_winner.append(cross_winner[j])  # int
                        order_volume.append(volume_listed_var[j])  # int
                        order_item.append(item_list[j])
                        order_sOrgOrdNo.append(sOrgOrdNo[j])
                        order_23_45.append(23)  # int
        # 차월물
        for i in range(self.center_index_45 - Up_CenterOption_Down, self.center_index_45 + Up_CenterOption_Down):
            for j in range(len(item_list)):
                if item_list[j][:3] == '201':
                    if self.output_call_option_data_45['code'][i] == item_list[j]:
                        order_index.append(i)  # int
                        order_cross_winner.append(cross_winner[j])  # int
                        order_volume.append(volume_listed_var[j])  # int
                        order_item.append(item_list[j])
                        order_sOrgOrdNo.append(sOrgOrdNo[j])
                        order_23_45.append(45)  # int

        for i in range(self.center_index_45 + Up_CenterOption_Down, self.center_index_45 - Up_CenterOption_Down, -1):
            for j in range(len(item_list)):
                if item_list[j][:3] == '301':
                    if self.output_put_option_data_45['code'][i] == item_list[j]:
                        order_index.append(i)  # int
                        order_cross_winner.append(cross_winner[j])  # int
                        order_volume.append(volume_listed_var[j])  # int
                        order_item.append(item_list[j])
                        order_sOrgOrdNo.append(sOrgOrdNo[j])
                        order_23_45.append(45)  # int
        # print(order_index)
        # print(order_cross_winner)
        # print(order_volume)
        # print(order_item)
        # print(order_sOrgOrdNo)
        # print(order_23_45)

        # 주문할 때 필요한 계좌 정보를 QComboBox 위젯으로부터
        accountrunVar = self.comboBox_acc.currentText()
        # "거래구분"(1:지정가, 2:조건부지정가, 3:시장가, 4:최유리지정가, 5:지정가IOC, 6:지정가FOK, 7:시장가IOC, 8:시장가FOK, 9:최유리IOC, A: 최유리FOK)
        sOrdTp = '1'
        # 주문 순차적으로 동시실행
        for i in range(len(order_item)):
            sRQName = order_item[i]
            sScreenNo = (i + 1001)
            CodeCallPut = order_item[i]
            # "주문수량"
            volumeVar = order_volume[i]

            # 선물
            # 당월물
            if order_23_45[i] == 11:
                if order_item[i] == self.futrue_s_data['item_code'][0]:
                    # 선물매수
                    if order_cross_winner[i] == 4004:
                        #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                        IOrdKind = 1
                        # "매매구분"(1:매도, 2:매수)
                        sslbyTp = '2'
                        # "주문가격"
                        PriceSellBuy = 'run_price'
                        # "주문가격"
                        Price = self.futrue_s_data[PriceSellBuy][order_index[i]]
                        # "원주문번호"
                        sOrgOrdNo_cell = order_sOrgOrdNo[i]
                    # 선물매도
                    elif order_cross_winner[i] == 6004:
                        #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                        IOrdKind = 1
                        # "매매구분"(1:매도, 2:매수)
                        sslbyTp = '1'
                        # "주문가격"
                        PriceSellBuy = 'run_price'
                        # "주문가격"
                        Price = self.futrue_s_data[PriceSellBuy][order_index[i]]
                        # "원주문번호"
                        sOrgOrdNo_cell = order_sOrgOrdNo[i]
            # 차월물
            elif order_23_45[i] == 22:
                if order_item[i] == self.futrue_s_data_45['item_code'][0]:
                    # 선물매수
                    if order_cross_winner[i] == 4004:
                        #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                        IOrdKind = 1
                        # "매매구분"(1:매도, 2:매수)
                        sslbyTp = '2'
                        # "주문가격"
                        PriceSellBuy = 'run_price'
                        # "주문가격"
                        Price = self.futrue_s_data_45[PriceSellBuy][order_index[i]]
                        # "원주문번호"
                        sOrgOrdNo_cell = order_sOrgOrdNo[i]
                    # 선물매도
                    elif order_cross_winner[i] == 6004:
                        #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                        IOrdKind = 1
                        # "매매구분"(1:매도, 2:매수)
                        sslbyTp = '1'
                        # "주문가격"
                        PriceSellBuy = 'run_price'
                        # "주문가격"
                        Price = self.futrue_s_data_45[PriceSellBuy][order_index[i]]
                        # "원주문번호"
                        sOrgOrdNo_cell = order_sOrgOrdNo[i]

            # 옵션
            # 당월물
            elif order_23_45[i] == 23:
                # 콜 매수
                if order_cross_winner[i] == 2004:
                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                    IOrdKind = 1
                    # "매매구분"(1:매도, 2:매수)
                    sslbyTp = '2'
                    # "주문가격"
                    PriceSellBuy = 'run_price'
                    # "주문가격"
                    Price = self.output_call_option_data[PriceSellBuy][order_index[i]]
                    # "원주문번호"
                    sOrgOrdNo_cell = order_sOrgOrdNo[i]

                # 풋 매수
                elif order_cross_winner[i] == 3004:
                    # "주문유형"(1:신규매매, 2:정정, 3:취소)
                    IOrdKind = 1
                    # "매매구분"(1:매도, 2:매수)
                    sslbyTp = '2'
                    # "주문가격"
                    PriceSellBuy = 'run_price'
                    # "주문가격"
                    Price = self.output_put_option_data[PriceSellBuy][order_index[i]]
                    # "원주문번호"
                    sOrgOrdNo_cell = order_sOrgOrdNo[i]

                # 콜 매도
                elif order_cross_winner[i] == 8004:
                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                    IOrdKind = 1
                    # "매매구분"(1:매도, 2:매수)
                    sslbyTp = '1'
                    # "주문가격"
                    PriceSellBuy = 'run_price'
                    # "주문가격"
                    Price = self.output_call_option_data[PriceSellBuy][order_index[i]]
                    # "원주문번호"
                    sOrgOrdNo_cell = order_sOrgOrdNo[i]

                # 풋 매도
                elif order_cross_winner[i] == 9004:
                    # "주문유형"(1:신규매매, 2:정정, 3:취소)
                    IOrdKind = 1
                    # "매매구분"(1:매도, 2:매수)
                    sslbyTp = '1'
                    # "주문가격"
                    PriceSellBuy = 'run_price'
                    # "주문가격"
                    Price = self.output_put_option_data[PriceSellBuy][order_index[i]]
                    # "원주문번호"
                    sOrgOrdNo_cell = order_sOrgOrdNo[i]

            # 차월물
            elif order_23_45[i] == 45:
                # 콜 매수
                if order_cross_winner[i] == 2004:
                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                    IOrdKind = 1
                    # "매매구분"(1:매도, 2:매수)
                    sslbyTp = '2'
                    # "주문가격"
                    PriceSellBuy = 'run_price'
                    # "주문가격"
                    Price = self.output_call_option_data_45[PriceSellBuy][order_index[i]]
                    # "원주문번호"
                    sOrgOrdNo_cell = order_sOrgOrdNo[i]

                # 풋 매수
                elif order_cross_winner[i] == 3004:
                    # "주문유형"(1:신규매매, 2:정정, 3:취소)
                    IOrdKind = 1
                    # "매매구분"(1:매도, 2:매수)
                    sslbyTp = '2'
                    # "주문가격"
                    PriceSellBuy = 'run_price'
                    # "주문가격"
                    Price = self.output_put_option_data_45[PriceSellBuy][order_index[i]]
                    # "원주문번호"
                    sOrgOrdNo_cell = order_sOrgOrdNo[i]

                # 콜 매도
                elif order_cross_winner[i] == 8004:
                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                    IOrdKind = 1
                    # "매매구분"(1:매도, 2:매수)
                    sslbyTp = '1'
                    # "주문가격"
                    PriceSellBuy = 'run_price'
                    # "주문가격"
                    Price = self.output_call_option_data_45[PriceSellBuy][order_index[i]]
                    # "원주문번호"
                    sOrgOrdNo_cell = order_sOrgOrdNo[i]

                # 풋 매도
                elif order_cross_winner[i] == 9004:
                    # "주문유형"(1:신규매매, 2:정정, 3:취소)
                    IOrdKind = 1
                    # "매매구분"(1:매도, 2:매수)
                    sslbyTp = '1'
                    # "주문가격"
                    PriceSellBuy = 'run_price'
                    # "주문가격"
                    Price = self.output_put_option_data_45[PriceSellBuy][order_index[i]]
                    # "원주문번호"
                    sOrgOrdNo_cell = order_sOrgOrdNo[i]

            # 선물옵션 주문명령
            # SendOrderFO("사용자구분요청명", "화면번호", "계좌번호", "종목코드", "주문유형"(1:신규매매, 2:정정, 3:취소),
            # "매매구분"(1:매도, 2:매수),
            # "거래구분"(1:지정가, 2:조건부지정가, 3:시장가, 4:최유리지정가, 5:지정가IOC, 6:지정가FOK, 7:시장가IOC, 8:시장가FOK, 9:최유리IOC, A: 최유리FOK),
            # "주문수량", "주문가격", "원주문번호")
            send_order_result_var = self.kiwoom.send_order(sRQName, sScreenNo, accountrunVar, CodeCallPut, IOrdKind, sslbyTp, sOrdTp, volumeVar, Price, sOrgOrdNo_cell)

            # 주문 전송결과 성공일때
            if send_order_result_var == 0:
                order_run_result_var = []
                order_run_result_var.append('전송')
                order_run_result_var.append(abs(int(sslbyTp)))
                order_run_result_var.append(CodeCallPut)
                order_run_result_var.append(volumeVar)
                order_run_result_var.append(Price)
                order_run_result_var.append(sOrgOrdNo_cell)
                # # 주문 실행 결과로
                # self.order_run_result(order_run_result_var)
            else:
                self.printt('전송실패')
                self.printt(send_order_result_var)

            # 서버요청 쉬어감
            time.sleep(TR_REQ_TIME_INTERVAL)

    # 주문 실행 결과
    def order_run_result(self, order_run_result_var):
        # order_run_result_var = []
        # order_run_result_var.append('전송')
        # order_run_result_var.append(send_order_result_var)
        # order_run_result_var.append(CodeCallPut)
        # order_run_result_var.append(volumeVar)
        # order_run_result_var.append(Price)
        # order_run_result_var.append(sOrgOrdNo)
        # order_run_result_var.append(OrderDealOk)

        # 시간표시
        current_time = time.ctime()
        self.printt(current_time)

        self.printt(order_run_result_var)

        if order_run_result_var[0] == '전송':
            self.printt('전송')

            # 주문 전송 결과
            self.order_trans_var['OrderRunKind'].append(order_run_result_var[0])
            self.order_trans_var['SellBuyType'].append(order_run_result_var[1])
            self.order_trans_var['OrderRunCode'].append(order_run_result_var[2])
            self.order_trans_var['OrderRunVolume'].append(order_run_result_var[3])
            self.order_trans_var['OrderRunPrice'].append(order_run_result_var[4])
            self.order_trans_var['OrgOrderNo'].append(order_run_result_var[5])
            self.order_trans_var['modify_item'].append(order_run_result_var[2])
            # 주문 접수 결과
            self.order_input_var['OrderRunKind'].append('')
            self.order_input_var['SellBuyType'].append(0)
            self.order_input_var['OrderRunCode'].append(order_run_result_var[2])
            self.order_input_var['OrderRunVolume'].append(0)
            self.order_input_var['OrderRunPrice'].append(0)
            self.order_input_var['OrgOrderNo'].append('')
            self.order_input_var['modify_item'].append('')
            # 주문 실행 결과
            self.order_result_var['OrderRunKind'].append('')
            self.order_result_var['SellBuyType'].append(0)
            self.order_result_var['OrderRunCode'].append(order_run_result_var[2])
            self.order_result_var['OrderRunVolume'].append(0)
            self.order_result_var['OrderRunPrice'].append(0)
            self.order_result_var['OrgOrderNo'].append('')
            self.order_result_var['modify_item'].append('')

        elif order_run_result_var[0] == '접수':
            self.printt('접수')
            # 접수
            self.printt(self.order_trans_var['OrgOrderNo'])
            if len(self.order_trans_var['OrderRunCode']) != 0:        # 이 프로그래에서 실행하지 않는 접수가 오는경우를 대비하여
                if not(order_run_result_var[5] in self.order_trans_var['OrgOrderNo']):      # 선물 정정 전송시 따라오는 접수번호는 원접수번호, 이므로 그 번호가 없을때만 접수변수에 저장(2021년 12월 7일 - 선물 트레이딩 작업시)

                    # # 타이머 중지
                    # self.timer1.stop()
                    # self.printt('타이머 중지')
                    # # 1분에 한번씩 클럭 발생
                    # self.timer60.start(1000 * 60)
                    # self.printt('정정 타이머 시작')
                    # # 진행바 표시(주문중)
                    # self.progressBar_order.setValue(100)
                    # 전송시 중지하던 정정타이머를 접수되면 중지하는것으로 변경(202211월 선물매도 신규불가능시에도 계속 정정타이머 작동하여 프로그램 모니터링 먹통 :: 선물옵션 기본예탁금 C형 1단계로 변겅처리하여 필요없어 보이지만...
                    # 그래도 전송되고 접수도 되지 않는 건으로 인하여 프로그램 에러를 방지하기 위하여~~~

                    for i in range(len(self.order_input_var['OrderRunCode'])):
                        if self.order_input_var['OrderRunCode'][i] == order_run_result_var[2]:

                            self.order_input_var['OrderRunKind'][i] = order_run_result_var[0]
                            self.order_input_var['SellBuyType'][i] = order_run_result_var[1]
                            self.order_input_var['OrderRunCode'][i] = order_run_result_var[2]
                            self.order_input_var['OrderRunVolume'][i] = order_run_result_var[3]
                            self.order_input_var['OrderRunPrice'][i] = order_run_result_var[4]
                            self.order_input_var['OrgOrderNo'][i] = order_run_result_var[5]
                            # 접수시 정정 아이템 종목 바인딩
                            self.order_input_var['modify_item'][i] = order_run_result_var[2]

        elif order_run_result_var[0] == '체결':
            self.printt('체결')
            OrderComplete_option = True
            self.printt('OrderComplete_option')
            self.printt(OrderComplete_option)
            # 체결
            if order_run_result_var[5] in self.order_input_var['OrgOrderNo']:      # 체결은 접수시의 접수번호가 있을때만
                for i in range(len(self.order_result_var['OrderRunCode'])):
                    if self.order_result_var['OrderRunCode'][i] == order_run_result_var[2]:

                        self.order_result_var['OrderRunKind'][i] = order_run_result_var[0]
                        self.order_result_var['SellBuyType'][i] = order_run_result_var[1]
                        self.order_result_var['OrderRunCode'][i] = order_run_result_var[2]
                        self.order_result_var['OrderRunVolume'][i] = order_run_result_var[3]
                        self.order_result_var['OrderRunPrice'][i] = order_run_result_var[4]
                        self.order_result_var['OrgOrderNo'][i] = order_run_result_var[5]

                        # 전송건수 와 체결건수 동일한지(종목코드 비교)
                        if self.order_result_var['OrderRunCode'][i] == self.order_trans_var['OrderRunCode'][i]:
                            if self.order_result_var['OrderRunVolume'][i] == self.order_trans_var['OrderRunVolume'][i]:
                                # 주문번호와 주문수량 동일::전송 정정 아이템
                                self.order_trans_var['modify_item'][i] = '전송vs체결수량OK'
                        # 2019년 3월 15일 12:05 - 1분 경과 정정 주문 실행 후 체결되어 정정아이템 지속발생 ~~
                        # 아래의 조건문에서 제외
                        # (self.order_trans_var['modify_item'][i] != '') or

                        # 접수건수 와 체결건수 동일한지(주문번호 비교)
                        if self.order_result_var['OrgOrderNo'][i] == self.order_input_var['OrgOrderNo'][i]:
                            if self.order_result_var['OrderRunVolume'][i] == self.order_input_var['OrderRunVolume'][i]:
                                # 주문번호와 주문수량 동일::접수 정정 아이템
                                self.order_input_var['modify_item'][i] = '접수vs체결수량OK'

                                # 매수/매도종목 텍스트 저장 호출
                                # 매도 매수 타입 # "매매구분"(1:매도, 2:매수)
                                if order_run_result_var[1] == 1:
                                    SellBuyType = '매도'
                                    # 시분초
                                    current_time = QTime.currentTime()
                                    text_time = current_time.toString('hh:mm:ss')
                                    time_msg = ' 체결완료 : ' + text_time
                                    # 텍스트 저장 호출
                                    self.printt_selled(order_run_result_var[2] + '::(' + SellBuyType + time_msg + ')')
                                elif order_run_result_var[1] == 2:
                                    SellBuyType = '매수'
                                    # 시분초
                                    current_time = QTime.currentTime()
                                    text_time = current_time.toString('hh:mm:ss')
                                    time_msg = ' 체결완료 : ' + text_time
                                    # 텍스트 저장 호출
                                    self.printt_buyed(order_run_result_var[2] + '::(' + SellBuyType + time_msg + ')')

                    if (self.order_input_var['modify_item'][i] != '접수vs체결수량OK'):
                        OrderComplete_option = False

                self.printt(self.order_trans_var['modify_item'])
                self.printt(self.order_input_var['modify_item'])
                self.printt(OrderComplete_option)
                if OrderComplete_option == True:
                    # 주문 결과
                    self.printt(self.order_trans_var)
                    self.printt(self.order_input_var)
                    self.printt(self.order_result_var)
                    # 주문 실행 결과
                    # 인스턴스 변수 선언
                    self.reset_order_var()

                    # 주문 타이머 시작
                    self.timer_order.start(1000 * 5)    # * 5 추가
                    self.printt('주문 타이머 시작')
                    # # 1분에 한번씩 클럭 발생(체결완료 되어 정정 타이머 중지)
                    # self.timer60.stop()
                    # self.printt('정정 타이머 중지')

    # 30초에 한번씩 클럭 발생(주문 체결 완료 결과)
    def timer_order_fn(self):
        # # 진행바 표시(주문중)
        # self.progressBar_order.setValue(0)
        # # 체결완료 정정 타이머 중지
        # self.timer60.stop()
        # self.printt('체결완료 정정 타이머 중지')

        # 주문 타이머 중지
        self.timer_order.stop()
        self.printt('주문 타이머 중지')

        # # 체결완료 1초 타이머 재시작
        # self.timer1.start(Future_s_Leverage_Int * 100)
        # self.printt('체결완료 1초 타이머 재시작')

    # 1분에 한번씩 클럭 발생::정정 주문 실행
    def timer1min(self):
        # 1분 타이머::정정 주문
        self.printt('1분 경과 정정 주문 실행')
        # 시간표시
        current_time = time.ctime()
        self.printt(current_time)
        self.printt(self.order_input_var['modify_item'])

        # 주문할 때 필요한 계좌 정보를 QComboBox 위젯으로부터
        accountrunVar = self.comboBox_acc.currentText()
        # "거래구분"(1:지정가, 2:조건부지정가, 3:시장가, 4:최유리지정가, 5:지정가IOC, 6:지정가FOK, 7:시장가IOC, 8:시장가FOK, 9:최유리IOC, A: 최유리FOK)
        sOrdTp = '1'
        # 주문 순차적으로 동시실행
        for i in range(len(self.order_input_var['modify_item'])):
            sRQName = self.order_input_var['modify_item'][i]
            sScreenNo = (i + 1001)
            # 종목코드 초기화
            CodeCallPut = '00000000'

            # 선물
            if self.order_input_var['modify_item'][i][:3] == '101':
                # 당월물
                if self.order_input_var['modify_item'][i] == self.futrue_s_data['item_code'][0]:
                    # 정정 아이템 건수(접수건수 - 체결건수)
                    modify_item_cnt = self.order_input_var['OrderRunVolume'][i] - \
                                      self.order_result_var['OrderRunVolume'][i]
                    if modify_item_cnt > 0:
                        # 매도/매수 구분 SellBuyType
                        if self.order_input_var['SellBuyType'][i] == 1:
                            # 매도일때
                            # 주문가격 클때
                            if self.order_input_var['OrderRunPrice'][i] > self.futrue_s_data['run_price'][0]:
                                #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                IOrdKind = 2
                                # "매매구분"(1:매도, 2:매수)
                                sslbyTp = self.order_input_var['SellBuyType'][i]
                                # "주문가격"
                                PriceSellBuy = 'run_price'
                                # "주문가격"
                                Price = self.futrue_s_data[PriceSellBuy][0]
                                # "원주문번호"
                                sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                # 종목코드
                                CodeCallPut = self.order_input_var['modify_item'][i]
                        elif self.order_input_var['SellBuyType'][i] == 2:
                            # 매수일때
                            # 주문가격 작을때
                            if self.order_input_var['OrderRunPrice'][i] < self.futrue_s_data['run_price'][0]:
                                #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                IOrdKind = 2
                                # "매매구분"(1:매도, 2:매수)
                                sslbyTp = self.order_input_var['SellBuyType'][i]
                                # "주문가격"
                                PriceSellBuy = 'run_price'
                                # "주문가격"
                                Price = self.futrue_s_data[PriceSellBuy][0]
                                # "원주문번호"
                                sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                # 종목코드
                                CodeCallPut = self.order_input_var['modify_item'][i]
                # 차월물
                elif self.order_input_var['modify_item'][i] == self.futrue_s_data_45['item_code'][0]:
                    # 정정 아이템 건수(접수건수 - 체결건수)
                    modify_item_cnt = self.order_input_var['OrderRunVolume'][i] - \
                                      self.order_result_var['OrderRunVolume'][i]
                    if modify_item_cnt > 0:
                        # 매도/매수 구분 SellBuyType
                        if self.order_input_var['SellBuyType'][i] == 1:
                            # 매도일때
                            # 주문가격 클때
                            if self.order_input_var['OrderRunPrice'][i] > self.futrue_s_data_45['run_price'][0]:
                                #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                IOrdKind = 2
                                # "매매구분"(1:매도, 2:매수)
                                sslbyTp = self.order_input_var['SellBuyType'][i]
                                # "주문가격"
                                PriceSellBuy = 'run_price'
                                # "주문가격"
                                Price = self.futrue_s_data_45[PriceSellBuy][0]
                                # "원주문번호"
                                sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                # 종목코드
                                CodeCallPut = self.order_input_var['modify_item'][i]
                        elif self.order_input_var['SellBuyType'][i] == 2:
                            # 매수일때
                            # 주문가격 작을때
                            if self.order_input_var['OrderRunPrice'][i] < self.futrue_s_data_45['run_price'][0]:
                                #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                IOrdKind = 2
                                # "매매구분"(1:매도, 2:매수)
                                sslbyTp = self.order_input_var['SellBuyType'][i]
                                # "주문가격"
                                PriceSellBuy = 'run_price'
                                # "주문가격"
                                Price = self.futrue_s_data_45[PriceSellBuy][0]
                                # "원주문번호"
                                sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                # 종목코드
                                CodeCallPut = self.order_input_var['modify_item'][i]
            # 옵션
            # 당월물
            # 콜
            elif self.order_input_var['modify_item'][i][:3] == '201':
                # 정정 아이템 건수(접수건수 - 체결건수)
                modify_item_cnt = self.order_input_var['OrderRunVolume'][i] - \
                                  self.order_result_var['OrderRunVolume'][i]
                if modify_item_cnt > 0:
                    # 매도/매수 구분 SellBuyType
                    if self.order_input_var['SellBuyType'][i] == 1:
                        # 매도일때
                        # 주문가격 클때
                        for j in range(self.center_index - Up_CenterOption_Down,
                                       self.center_index + Up_CenterOption_Down):
                            if self.order_input_var['OrderRunCode'][i] == self.output_call_option_data['code'][j]:
                                # 원 주문가격과 현재의 주문가격이 다를때만
                                if self.order_input_var['OrderRunPrice'][i] > \
                                        self.output_call_option_data['run_price'][j]:
                                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                    IOrdKind = 2
                                    # "매매구분"(1:매도, 2:매수)
                                    sslbyTp = self.order_input_var['SellBuyType'][i]
                                    # "주문가격"
                                    PriceSellBuy = 'run_price'
                                    # "주문가격"
                                    Price = self.output_call_option_data[PriceSellBuy][j]
                                    # "원주문번호"
                                    sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                    # 종목코드
                                    CodeCallPut = self.order_input_var['modify_item'][i]
                    elif self.order_input_var['SellBuyType'][i] == 2:
                        # 매수일때
                        # 주문가격 작을때
                        for j in range(self.center_index - Up_CenterOption_Down,
                                       self.center_index + Up_CenterOption_Down):
                            if self.order_input_var['OrderRunCode'][i] == self.output_call_option_data['code'][j]:
                                # 원 주문가격과 현재의 주문가격이 다를때만
                                if self.order_input_var['OrderRunPrice'][i] < \
                                        self.output_call_option_data['run_price'][j]:
                                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                    IOrdKind = 2
                                    # "매매구분"(1:매도, 2:매수)
                                    sslbyTp = self.order_input_var['SellBuyType'][i]
                                    # "주문가격"
                                    PriceSellBuy = 'run_price'
                                    # "주문가격"
                                    Price = self.output_call_option_data[PriceSellBuy][j]
                                    # "원주문번호"
                                    sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                    # 종목코드
                                    CodeCallPut = self.order_input_var['modify_item'][i]

            # 풋
            elif self.order_input_var['modify_item'][i][:3] == '301':
                # 정정 아이템 건수(접수건수 - 체결건수)
                modify_item_cnt = self.order_input_var['OrderRunVolume'][i] - \
                                  self.order_result_var['OrderRunVolume'][i]

                # 20230114 test
                self.printt('정정 아이템 건수(접수건수 - 체결건수)')
                self.printt(self.order_input_var['OrderRunVolume'][i])
                self.printt(self.order_result_var['OrderRunVolume'][i])

                if modify_item_cnt > 0:

                    # 20230114 test
                    self.printt('정정 아이템 건수(접수건수 - 체결건수)')
                    self.printt(modify_item_cnt)

                    # 매도/매수 구분 SellBuyType
                    if self.order_input_var['SellBuyType'][i] == 1:
                        # 매도일때
                        # 주문가격 클때
                        for j in range(self.center_index + Up_CenterOption_Down,
                                       self.center_index - Up_CenterOption_Down, -1):
                            if self.order_input_var['OrderRunCode'][i] == self.output_put_option_data['code'][j]:
                                # 원 주문가격과 현재의 주문가격이 다를때만
                                if self.order_input_var['OrderRunPrice'][i] > \
                                        self.output_put_option_data['run_price'][j]:

                                    # 20230114 test
                                    self.printt('원 주문가격과 현재의 주문가격이 다를때만')
                                    self.printt(self.order_input_var['OrderRunPrice'][i])
                                    self.printt(self.output_put_option_data_45['run_price'][j])

                                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                    IOrdKind = 2
                                    # "매매구분"(1:매도, 2:매수)
                                    sslbyTp = self.order_input_var['SellBuyType'][i]
                                    # "주문가격"
                                    PriceSellBuy = 'run_price'
                                    # "주문가격"
                                    Price = self.output_put_option_data[PriceSellBuy][j]
                                    # "원주문번호"
                                    sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                    # 종목코드
                                    CodeCallPut = self.order_input_var['modify_item'][i]
                    elif self.order_input_var['SellBuyType'][i] == 2:
                        # 매수일때
                        # 주문가격 작을때
                        for j in range(self.center_index + Up_CenterOption_Down,
                                       self.center_index - Up_CenterOption_Down, -1):
                            if self.order_input_var['OrderRunCode'][i] == self.output_put_option_data['code'][j]:
                                # 원 주문가격과 현재의 주문가격이 다를때만
                                if self.order_input_var['OrderRunPrice'][i] < \
                                        self.output_put_option_data['run_price'][j]:
                                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                    IOrdKind = 2
                                    # "매매구분"(1:매도, 2:매수)
                                    sslbyTp = self.order_input_var['SellBuyType'][i]
                                    # "주문가격"
                                    PriceSellBuy = 'run_price'
                                    # "주문가격"
                                    Price = self.output_put_option_data[PriceSellBuy][j]
                                    # "원주문번호"
                                    sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                    # 종목코드
                                    CodeCallPut = self.order_input_var['modify_item'][i]
            # 차월물
            # 콜
            elif self.order_input_var['modify_item'][i][:3] == '201':
                # 정정 아이템 건수(접수건수 - 체결건수)
                modify_item_cnt = self.order_input_var['OrderRunVolume'][i] - \
                                  self.order_result_var['OrderRunVolume'][i]
                if modify_item_cnt > 0:
                    # 매도/매수 구분 SellBuyType
                    if self.order_input_var['SellBuyType'][i] == 1:
                        # 매도일때
                        # 주문가격 클때
                        for j in range(self.center_index_45 - Up_CenterOption_Down,
                                       self.center_index_45 + Up_CenterOption_Down):
                            if self.order_input_var['OrderRunCode'][i] == self.output_call_option_data_45['code'][j]:
                                # 원 주문가격과 현재의 주문가격이 다를때만
                                if self.order_input_var['OrderRunPrice'][i] > \
                                        self.output_call_option_data_45['run_price'][j]:
                                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                    IOrdKind = 2
                                    # "매매구분"(1:매도, 2:매수)
                                    sslbyTp = self.order_input_var['SellBuyType'][i]
                                    # "주문가격"
                                    PriceSellBuy = 'run_price'
                                    # "주문가격"
                                    Price = self.output_call_option_data_45[PriceSellBuy][j]
                                    # "원주문번호"
                                    sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                    # 종목코드
                                    CodeCallPut = self.order_input_var['modify_item'][i]
                    elif self.order_input_var['SellBuyType'][i] == 2:
                        # 매수일때
                        # 주문가격 작을때
                        for j in range(self.center_index_45 - Up_CenterOption_Down,
                                       self.center_index_45 + Up_CenterOption_Down):
                            if self.order_input_var['OrderRunCode'][i] == self.output_call_option_data_45['code'][j]:
                                # 원 주문가격과 현재의 주문가격이 다를때만
                                if self.order_input_var['OrderRunPrice'][i] < \
                                        self.output_call_option_data_45['run_price'][j]:
                                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                    IOrdKind = 2
                                    # "매매구분"(1:매도, 2:매수)
                                    sslbyTp = self.order_input_var['SellBuyType'][i]
                                    # "주문가격"
                                    PriceSellBuy = 'run_price'
                                    # "주문가격"
                                    Price = self.output_call_option_data_45[PriceSellBuy][j]
                                    # "원주문번호"
                                    sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                    # 종목코드
                                    CodeCallPut = self.order_input_var['modify_item'][i]
            # 풋
            elif self.order_input_var['modify_item'][i][:3] == '301':
                # 정정 아이템 건수(접수건수 - 체결건수)
                modify_item_cnt = self.order_input_var['OrderRunVolume'][i] - \
                                  self.order_result_var['OrderRunVolume'][i]

                # 20230114 test
                self.printt('정정 아이템 건수(접수건수 - 체결건수)')
                self.printt(self.order_input_var['OrderRunVolume'][i])
                self.printt(self.order_result_var['OrderRunVolume'][i])

                if modify_item_cnt > 0:

                    # 20230114 test
                    self.printt('정정 아이템 건수(접수건수 - 체결건수)')
                    self.printt(modify_item_cnt)

                    # 매도/매수 구분 SellBuyType
                    if self.order_input_var['SellBuyType'][i] == 1:
                        # 매도일때
                        # 주문가격 클때
                        for j in range(self.center_index_45 + Up_CenterOption_Down,
                                       self.center_index_45 - Up_CenterOption_Down, -1):
                            if self.order_input_var['OrderRunCode'][i] == self.output_put_option_data_45['code'][j]:
                                # 원 주문가격과 현재의 주문가격이 다를때만
                                if self.order_input_var['OrderRunPrice'][i] > \
                                        self.output_put_option_data_45['run_price'][j]:

                                    # 20230114 test
                                    self.printt('원 주문가격과 현재의 주문가격이 다를때만')
                                    self.printt(self.order_input_var['OrderRunPrice'][i])
                                    self.printt(self.output_put_option_data_45['run_price'][j])

                                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                    IOrdKind = 2
                                    # "매매구분"(1:매도, 2:매수)
                                    sslbyTp = self.order_input_var['SellBuyType'][i]
                                    # "주문가격"
                                    PriceSellBuy = 'run_price'
                                    # "주문가격"
                                    Price = self.output_put_option_data_45[PriceSellBuy][j]
                                    # "원주문번호"
                                    sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                    # 종목코드
                                    CodeCallPut = self.order_input_var['modify_item'][i]
                    elif self.order_input_var['SellBuyType'][i] == 2:
                        # 매수일때
                        # 주문가격 작을때
                        for j in range(self.center_index_45 + Up_CenterOption_Down,
                                       self.center_index_45 - Up_CenterOption_Down, -1):
                            if self.order_input_var['OrderRunCode'][i] == self.output_put_option_data_45['code'][j]:
                                # 원 주문가격과 현재의 주문가격이 다를때만
                                if self.order_input_var['OrderRunPrice'][i] < \
                                        self.output_put_option_data_45['run_price'][j]:
                                    #  "주문유형"(1:신규매매, 2:정정, 3:취소)
                                    IOrdKind = 2
                                    # "매매구분"(1:매도, 2:매수)
                                    sslbyTp = self.order_input_var['SellBuyType'][i]
                                    # "주문가격"
                                    PriceSellBuy = 'run_price'
                                    # "주문가격"
                                    Price = self.output_put_option_data_45[PriceSellBuy][j]
                                    # "원주문번호"
                                    sOrgOrdNo_cell = self.order_input_var['OrgOrderNo'][i]
                                    # 종목코드
                                    CodeCallPut = self.order_input_var['modify_item'][i]

            self.printt('정정 주문 실행 여부')
            self.printt(CodeCallPut[:3])

            # 신규주문과 달리 정정주문은 사전 종목검색 별도 없으므로 현재의 주문종목 코드가 [선물/콜/옵션] 일때만 주문실행
            if CodeCallPut[:3] in ['101', '201', '301']:
                # 선물옵션 주문명령
                # SendOrderFO("사용자구분요청명", "화면번호", "계좌번호", "종목코드", "주문유형"(1:신규매매, 2:정정, 3:취소),
                # "매매구분"(1:매도, 2:매수),
                # "거래구분"(1:지정가, 2:조건부지정가, 3:시장가, 4:최유리지정가, 5:지정가IOC, 6:지정가FOK, 7:시장가IOC, 8:시장가FOK, 9:최유리IOC, A: 최유리FOK),
                # "주문수량", "주문가격", "원주문번호")
                send_order_result_var = self.kiwoom.send_order(sRQName, sScreenNo, accountrunVar, CodeCallPut, IOrdKind, sslbyTp, sOrdTp, modify_item_cnt, Price, sOrgOrdNo_cell)

                # 주문 전송결과 성공일때
                if send_order_result_var == 0:
                    # 원접수번호 바인딩(신규주문시에는 '', 정정주문시에는 원주문번호 전송됨) 구분을 위하여
                    self.order_trans_var['OrgOrderNo'][i] = sOrgOrdNo_cell
                    self.printt('정정 전송성공')
                    self.printt(send_order_result_var)
                else:
                    self.printt('전송실패')
                    self.printt(send_order_result_var)

                # 서버요청 쉬어감
                time.sleep(TR_REQ_TIME_INTERVAL)
                # 서버 주문전송 이후로 변경(2021년 12월 10일 :: 선물 옵션 정정 및 주문 전송 대대적 수정시





    # 다음 변경시 체결 않된건 취소
    def cancel_order(self, item_list_cnt_type):
        self.printt('다음 변경시 체결 않된건 취소')
        # 시간표시
        current_time = time.ctime()
        self.printt(current_time)
        self.printt(item_list_cnt_type)

        # 주문할 때 필요한 계좌 정보를 QComboBox 위젯으로부터
        accountrunVar = self.comboBox_acc.currentText()
        # 주문 순차적으로 동시실행
        for i in range(len(item_list_cnt_type['code_no'])):
            sRQName = item_list_cnt_type['code_no'][i]
            sScreenNo = (i + 3001)
            # 종목코드
            CodeCallPut = item_list_cnt_type['code_no'][i]
            #  "주문유형"(1:신규매매, 2:정정, 3:취소)
            IOrdKind = 3
            # "매매구분"(1:매도, 2:매수)
            sslbyTp = item_list_cnt_type['sell_buy_type'][i]
            # "거래구분"(1:지정가, 2:조건부지정가, 3:시장가, 4:최유리지정가, 5:지정가IOC, 6:지정가FOK, 7:시장가IOC, 8:시장가FOK, 9:최유리IOC, A: 최유리FOK)
            sOrdTp = '1'
            # "주문수량"
            cancel_item_cnt = item_list_cnt_type['cnt'][i]
            # "주문가격"
            Price = 0.0
            # "원주문번호"
            sOrgOrdNo_cell = item_list_cnt_type['order_no'][i]

            self.printt('# 취소 주문 실행 - 종목코드 앞자리[:3]')
            self.printt(CodeCallPut[:3])

            # 신규주문과 달리 취소 주문은 사전 종목검색 별도 없으므로 현재의 주문종목 코드가 [선물/콜/옵션] 일때만 주문실행
            if CodeCallPut[:3] in ['101', '201', '301']:    # 주문 취소시 선물주문 취소는 예외(선물 옵션 정정주문 예외시)20240104
                # 선물옵션 주문명령
                # SendOrderFO("사용자구분요청명", "화면번호", "계좌번호", "종목코드", "주문유형"(1:신규매매, 2:정정, 3:취소),
                # "매매구분"(1:매도, 2:매수),
                # "거래구분"(1:지정가, 2:조건부지정가, 3:시장가, 4:최유리지정가, 5:지정가IOC, 6:지정가FOK, 7:시장가IOC, 8:시장가FOK, 9:최유리IOC, A: 최유리FOK),
                # "주문수량", "주문가격", "원주문번호")
                send_order_result_var = self.kiwoom.send_order(sRQName, sScreenNo, accountrunVar, CodeCallPut, IOrdKind, sslbyTp, sOrdTp, cancel_item_cnt, Price, sOrgOrdNo_cell)

                # 주문 전송결과 성공일때
                if send_order_result_var == 0:
                    self.printt('# 취소 전송성공')
                    self.printt(send_order_result_var)
                else:
                    self.printt('# 전송실패')
                    self.printt(send_order_result_var)

                # 서버요청 쉬어감
                time.sleep(TR_REQ_TIME_INTERVAL)
                # 서버 주문전송 이후로 변경(2021년 12월 10일 :: 선물 옵션 정정 및 주문 전송 대대적 수정시










    # stock 주문 실행 결과
    # 인스턴스 변수 선언
    def reset_order_var_stock(self):
        self.order_trans_var_stock = {'OrderRunKind': [], 'SellBuyType': [], 'OrderRunCode': [], 'OrderRunVolume': [],
                                'OrderRunPrice': [], 'OrgOrderNo': [], 'modify_item': []}
        self.order_input_var_stock = {'OrderRunKind': [], 'SellBuyType': [], 'OrderRunCode': [], 'OrderRunVolume': [],
                                'OrderRunPrice': [], 'OrgOrderNo': [], 'modify_item': []}
        self.order_result_var_stock = {'OrderRunKind': [], 'SellBuyType': [], 'OrderRunCode': [], 'OrderRunVolume': [],
                                 'OrderRunPrice': [], 'OrgOrderNo': [], 'modify_item': []}

    # send_order_stock 메서드에서는 사용자가 위젯을 통해 입력한 정보를 얻어온 후 이를 이용해 Kiwoom 클래스에 구현돼 있는 send_order 메서드를 호출
    def order_ready_stock(self, cross_winner, volume_listed_var, item_list, sOrgOrdNo):
        # 주문 종목 인텍스 찾기
        order_index = []
        order_cross_winner = []
        order_volume = []
        order_item = []
        order_sOrgOrdNo = []
        for i in range(len(self.stock_item_data['stock_item_no'])):
            for j in range(len(item_list)):
                if self.stock_item_data['stock_item_no'][i] == item_list[j]:
                    order_index.append(i)
                    order_cross_winner.append(cross_winner[j])
                    order_volume.append(volume_listed_var[j])
                    order_item.append(item_list[j])
                    order_sOrgOrdNo.append(sOrgOrdNo[j])

                    # -----
                    # stock "체결"과 무관하게 텍스트 저장
                    # 매수/매도종목 텍스트 저장 호출
                    # 매도 매수 타입 # "매매구분"(1:매도, 2:매수)
                    if cross_winner[j] == 7004:
                        SellBuyType = '매도'
                        # 시분초
                        current_time = QTime.currentTime()
                        text_time = current_time.toString('hh:mm:ss')
                        time_msg = ' order 주문전 : ' + text_time
                        # 텍스트 저장 호출
                        self.printt_selled(item_list[j] + '::(' + SellBuyType + time_msg + ')')
                    elif cross_winner[j] == 1004:
                        SellBuyType = '매수'
                        # 시분초
                        current_time = QTime.currentTime()
                        text_time = current_time.toString('hh:mm:ss')
                        time_msg = ' order 주문전 : ' + text_time
                        # 텍스트 저장 호출
                        self.printt_buyed(item_list[j] + '::(' + SellBuyType + time_msg + ')')
                    # 전송이후 매도/매수 텍스트를 저장하니, 매도 검색이 "체결" 실시간이므로
                    # 반복적으로 발생되는것을 방지하기 위하여 [stock order 바로 주문전] 위치로 변경[20240129]
                    # -----

        self.printt('stock order 바로 주문전')
        self.printt(order_index)
        self.printt(order_item)
        self.printt(order_volume)

        # 주문할 때 필요한 계좌 정보를 QComboBox 위젯으로부터
        accountrunVar = self.comboBox_acc_stock.currentText()
        # "거래구분"(00 : 지정가  /  03 : 시장가)
        sHogaGb = '00'
        # 주문 순차적으로 동시실행
        for i in range(len(order_item)):
            sRQName = order_item[i]
            sScreenNo = order_index[i]
            CodeStock = order_item[i]
            # "주문수량"
            volumeVar = order_volume[i]

            # 매수
            if order_cross_winner[i] == 1004:
                #  "주문유형"(주문유형 1:신규매수, 2:신규매도 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정)
                IOrdKind = 1
                # "매매구분"(1:매도, 2:매수)
                sslbyTp = 2
                # "주문가격"
                PriceSellBuy = 'stock_end'
                # "주문가격"
                Price = self.stock_item_data[PriceSellBuy][order_index[i]]
                # "원주문번호"
                sOrgOrdNo_cell = order_sOrgOrdNo[i]

            # 매도
            elif order_cross_winner[i] == 7004:
                #  "주문유형"(주문유형 1:신규매수, 2:신규매도 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정)
                IOrdKind = 2
                # "매매구분"(1:매도, 2:매수)
                sslbyTp = 1
                # "주문가격"
                PriceSellBuy = 'stock_end'
                # "주문가격"
                Price = self.stock_item_data[PriceSellBuy][order_index[i]]
                # "원주문번호"
                sOrgOrdNo_cell = order_sOrgOrdNo[i]

            # 주식 주문명령
            # SendOrderFO("사용자구분요청명", "화면번호", "계좌번호", "주문유형"(1:신규매수, 2:신규매도 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정),
            # "종목코드",
            # "주문수량", "주문가격"
            # "거래구분"(00 : 지정가                #           03 : 시장가),
            # "원주문번호"
            send_order_result_var = self.kiwoom.send_order_stock(sRQName, sScreenNo, accountrunVar, IOrdKind, CodeStock, volumeVar, Price, sHogaGb, sOrgOrdNo_cell)

            # 주문 전송결과 성공일때
            if send_order_result_var == 0:
                order_run_result_var = []
                order_run_result_var.append('전송')
                order_run_result_var.append(abs(int(sslbyTp)))
                order_run_result_var.append(CodeStock)
                order_run_result_var.append(abs(int(volumeVar)))
                order_run_result_var.append(abs(int(Price)))
                order_run_result_var.append(sOrgOrdNo_cell)
                # # 주문 실행 결과로
                # self.order_run_result_stock(order_run_result_var)
            else:
                self.printt('전송실패')
                self.printt(send_order_result_var)
            # 서버요청 쉬어감
            time.sleep(TR_REQ_TIME_INTERVAL)

    # 주문 실행 결과
    def order_run_result_stock(self, order_run_result_var):
        # order_run_result_var = []
        # order_run_result_var.append('전송')
        # order_run_result_var.append(send_order_result_var)
        # order_run_result_var.append(CodeStock)
        # order_run_result_var.append(volumeVar)
        # order_run_result_var.append(Price)
        # order_run_result_var.append(sOrgOrdNo)
        # order_run_result_var.append(OrderDealOk)

        # 시간표시
        current_time = time.ctime()
        self.printt(current_time)

        self.printt(order_run_result_var)

        # # 타이머 중지
        # self.timer1.stop()
        # self.printt('타이머 중지')
        # # 1분에 한번씩 클럭 발생
        # self.timer60.start(1000 * 60)
        # self.printt('정정 타이머 시작')
        # # 진행바 표시(주문중)
        # self.progressBar_order.setValue(100)

        if order_run_result_var[0] == '전송':
            self.printt('전송')

            # 주문 전송 결과
            self.order_trans_var_stock['OrderRunKind'].append(order_run_result_var[0])
            self.order_trans_var_stock['SellBuyType'].append(order_run_result_var[1])
            self.order_trans_var_stock['OrderRunCode'].append(order_run_result_var[2])
            self.order_trans_var_stock['OrderRunVolume'].append(order_run_result_var[3])
            self.order_trans_var_stock['OrderRunPrice'].append(order_run_result_var[4])
            self.order_trans_var_stock['OrgOrderNo'].append(order_run_result_var[5])
            self.order_trans_var_stock['modify_item'].append(order_run_result_var[2])
            # 주문 접수 결과
            self.order_input_var_stock['OrderRunKind'].append('')
            self.order_input_var_stock['SellBuyType'].append(0)
            self.order_input_var_stock['OrderRunCode'].append(order_run_result_var[2])
            self.order_input_var_stock['OrderRunVolume'].append(0)
            self.order_input_var_stock['OrderRunPrice'].append(0)
            self.order_input_var_stock['OrgOrderNo'].append('')
            self.order_input_var_stock['modify_item'].append('')
            # 주문 실행 결과
            self.order_result_var_stock['OrderRunKind'].append('')
            self.order_result_var_stock['SellBuyType'].append(0)
            self.order_result_var_stock['OrderRunCode'].append(order_run_result_var[2])
            self.order_result_var_stock['OrderRunVolume'].append(0)
            self.order_result_var_stock['OrderRunPrice'].append(0)
            self.order_result_var_stock['OrgOrderNo'].append('')
            self.order_result_var_stock['modify_item'].append('')

            # print(self.order_trans_var_stock)
            # print(self.order_input_var_stock)
            # print(self.order_result_var_stock)

        elif order_run_result_var[0] == '접수':
            self.printt('접수')

            # 접수
            for i in range(len(self.order_input_var_stock['OrderRunCode'])):
                if self.order_input_var_stock['modify_item'][i] != '접수vs체결수량OK':
                    if self.order_input_var_stock['OrderRunCode'][i] == order_run_result_var[2]:

                        self.order_input_var_stock['OrderRunKind'][i] = order_run_result_var[0]
                        self.order_input_var_stock['SellBuyType'][i] = order_run_result_var[1]
                        self.order_input_var_stock['OrderRunCode'][i] = order_run_result_var[2]
                        self.order_input_var_stock['OrderRunVolume'][i] = order_run_result_var[3]
                        self.order_input_var_stock['OrderRunPrice'][i] = order_run_result_var[4]
                        self.order_input_var_stock['OrgOrderNo'][i] = order_run_result_var[5]
                        # 접수시 정정 아이템 종목 바인딩
                        self.order_input_var_stock['modify_item'][i] = order_run_result_var[2]

        elif order_run_result_var[0] == '체결':
            self.printt('체결')
            OrderComplete_stock = True
            self.printt('OrderComplete_stock')
            self.printt(OrderComplete_stock)
            # 체결
            for i in range(len(self.order_result_var_stock['OrderRunCode'])):
                if self.order_input_var_stock['modify_item'][i] != '접수vs체결수량OK':
                    if self.order_result_var_stock['OrderRunCode'][i] == order_run_result_var[2]:

                        self.order_result_var_stock['OrderRunKind'][i] = order_run_result_var[0]
                        self.order_result_var_stock['SellBuyType'][i] = order_run_result_var[1]
                        self.order_result_var_stock['OrderRunCode'][i] = order_run_result_var[2]
                        self.order_result_var_stock['OrderRunVolume'][i] = order_run_result_var[3]
                        self.order_result_var_stock['OrderRunPrice'][i] = order_run_result_var[4]
                        self.order_result_var_stock['OrgOrderNo'][i] = order_run_result_var[5]

                        # 접수건수 와 체결건수 동일한지(주문번호 비교)
                        if self.order_result_var_stock['OrgOrderNo'][i] == self.order_input_var_stock['OrgOrderNo'][i]:
                            if self.order_result_var_stock['OrderRunVolume'][i] == self.order_input_var_stock['OrderRunVolume'][i]:

                                # 재고조회가 타이머 작동후 1초 지나서 되므로 체결완료시 보유한 해당 종목 수량제외
                                for have in range(len(self.stock_have_data['stock_no'])):
                                    if self.stock_have_data['stock_no'][have] == order_run_result_var[2]:
                                        # 매도일때 해당종목 보유종목을 0
                                        if order_run_result_var[1] == 1:
                                            self.stock_have_data['myhave_cnt'][have] = 0

                                # 매수/매도종목 텍스트 저장 호출
                                # 매도 매수 타입 # "매매구분"(1:매도, 2:매수)
                                if order_run_result_var[1] == 1:
                                    SellBuyType = '매도'
                                    # 시분초
                                    current_time = QTime.currentTime()
                                    text_time = current_time.toString('hh:mm:ss')
                                    time_msg = ' 체결완료 : ' + text_time
                                    # 텍스트 저장 호출
                                    self.printt_selled(order_run_result_var[2] + '::(' + SellBuyType + time_msg + ')')

                                elif order_run_result_var[1] == 2:
                                    SellBuyType = '매수'
                                    # 시분초
                                    current_time = QTime.currentTime()
                                    text_time = current_time.toString('hh:mm:ss')
                                    time_msg = ' 체결완료 : ' + text_time
                                    # 텍스트 저장 호출
                                    self.printt_buyed(order_run_result_var[2] + '::(' + SellBuyType + time_msg + ')')

                                # 주문번호와 주문수량 동일::접수 정정 아이템 공백
                                self.order_input_var_stock['modify_item'][i] = '접수vs체결수량OK'

                        # 전송건수 와 체결건수 동일한지(종목코드 비교)
                        if self.order_result_var_stock['OrderRunCode'][i] == self.order_trans_var_stock['OrderRunCode'][i]:
                            if self.order_result_var_stock['OrderRunVolume'][i] == self.order_trans_var_stock['OrderRunVolume'][i]:

                                # 주문번호와 주문수량 동일::전송 정정 아이템 공백
                                self.order_trans_var_stock['modify_item'][i] = '전송vs체결수량OK'

                    if self.order_input_var_stock['modify_item'][i] != '접수vs체결수량OK':
                        OrderComplete_stock = False

            self.printt(self.order_trans_var_stock['modify_item'])
            self.printt(self.order_input_var_stock['modify_item'])
            self.printt(OrderComplete_stock)
            if OrderComplete_stock == True:
                # # 타이머 중지  ## stock option 동시주문시 stock에 의해서 self.timer1.start(Future_s_Leverage_Int * 100) 않됨
                # self.timer1.stop()
                # self.printt('stock 접수vs체결수량OK timer1 중지')
                # # 주문 타이머 시작
                # self.timer_order_stock.start(1000)
                # self.printt('stock 주문타이머 시작')

                # 1초 메인 타이머와 중복으로 에러발생 가능성 :: stock 주문타이머 작동않하고 아래의 내용만 출력함으로 대체
                # 주식매도시 stock_have_data['myhave_cnt'][have] > 0 체크하므로 이상없을것으로 판단
                # 주문결과
                self.printt(self.order_trans_var_stock)
                self.printt(self.order_input_var_stock)
                self.printt(self.order_result_var_stock)

    # 1초에 한번씩 클럭 발생(주문 체결 완료 결과)
    def timer_order_fn_stock(self):
        # 주문결과
        self.printt(self.order_trans_var_stock)
        self.printt(self.order_input_var_stock)
        self.printt(self.order_result_var_stock)

        # 계좌평가잔고내역요청[stock]
        self.stock_have_data_rq()
        # # 테이블 위젯에 표시하기
        # self.stock_listed_slot(self.stock_have_data)

        # 주문타이머 중지
        self.timer_order_stock.stop()
        self.printt('stock 주문타이머 중지')
        # # 타이머 시작
        # self.timer1.start(Future_s_Leverage_Int * 100)
        # self.printt('stock 주문체결완료 timer1 재시작')

    # 주식매도 종목검색
    def stock_sell_items_search(self, strCode):
        sell_item_list = []
        market_out_cnt = 0
        for i in range(len(self.stock_have_data['stock_no'])):
            # 종목코드 같을때
            if self.stock_have_data['stock_no'][i] == strCode:
                # 재고있을때
                if self.stock_have_data['myhave_cnt'][i] > 0:
                    # 매도건수 체크
                    market_out_cnt = self.tarket_earn_cnt_fn(strCode)
                    # 매도건수 0이상이면
                    if market_out_cnt > 0:
                        # 당일 매도 종목 찾기
                        self.selled_today_items = self.selled_today_items_search_fn()
                        # self.printt('# 당일 매도 종목 찾기')
                        # self.printt(self.selled_today_items)
                        # 오늘 매도목록에 있으면 통과
                        if strCode not in self.selled_today_items:
                            sell_item_list.append(strCode)
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            self.printt('-----')
                            self.printt('매도종목검색 실행시간 : ' + text_time)
                            self.printt('poly_sell_max_price 기준초과 item_list')
                            self.printt('sell_item_list / market_out_cnt')
                            self.printt(sell_item_list)
                            self.printt(market_out_cnt)
                            self.printt('market_in_price / run_price')
                            self.printt(format(self.stock_have_data['market_in_price'][i], ','))
                            self.printt(format(self.stock_have_data['run_price'][i], ','))
        if len(sell_item_list) > 0:
            cross_winner = []
            volume_listed_var = []
            item_list = []
            sOrgOrdNo = []
            self.printt('poly_sell_max_price 기준초과 청산')
            cross_winner_cell = 7004
            self.printt(cross_winner_cell)
            sOrgOrdNo_cell = ''
            for i in range(len(self.stock_have_data['stock_no'])):
                for have in range(len(sell_item_list)):
                    if self.stock_have_data['stock_no'][i] == sell_item_list[have]:
                        if self.stock_have_data['myhave_cnt'][i] > 0:
                            cross_winner.append(cross_winner_cell)
                            volume_listed_var.append(market_out_cnt)
                            item_list.append(sell_item_list[have])
                            sOrgOrdNo.append(sOrgOrdNo_cell)
            self.printt(item_list)
            # 주문준비 완료
            self.order_ready_stock(cross_winner, volume_listed_var, item_list, sOrgOrdNo)

    # 목표건수 구하기(tarket_earn_cnt_fn)
    def tarket_earn_cnt_fn(self, strCode):
        #  ai로 구한값 매도처리
        # if self.stock_trend_line_of_ai_day != None:
        for i in range(len(self.stock_trend_line_of_ai_day['stock_no'])):
            for k in range(len(self.stock_have_data['stock_no'])):
                if self.stock_have_data['stock_no'][k] == strCode:
                    if self.stock_trend_line_of_ai_day['stock_no'][i] == strCode:
                        each_run_price = self.stock_have_data['run_price'][k]
                        each_sell_max_price = self.stock_trend_line_of_ai_day['poly_sell_max_price'][i]
                        if each_sell_max_price < each_run_price:
                            # 모든조건 만족 매도건수 구하기
                            sell_market_out_cnt_int = int(math.floor(self.market_in_percent_won / self.stock_have_data['run_price'][k]))
                            # 매도가능 건수
                            if sell_market_out_cnt_int >= self.stock_have_data['myhave_cnt'][k]:
                                return self.stock_have_data['myhave_cnt'][k]
                            elif sell_market_out_cnt_int < self.stock_have_data['myhave_cnt'][k]:
                                # self.printt('buy_market_in_cnt')
                                # self.printt(buy_market_in_cnt)
                                # self.printt(buy_market_in_cnt_int)
                                return sell_market_out_cnt_int
                            elif sell_market_out_cnt_int == 0:
                                sell_market_out_cnt_int = 0
                                # self.printt('sell_market_out_cnt_int = 0')
                                # self.printt(sell_market_out_cnt_int)
                                return sell_market_out_cnt_int
        return 0

    # 주식매수 종목검색
    def stock_buy_items_search(self, stock_tarket_item_list):
        # 매수종목 추가시 가능금액 차감
        buy_able_money = self.buy_able_money
        if len(stock_tarket_item_list) > 0:
            cross_winner = []
            volume_listed_var = []
            item_list = []
            sOrgOrdNo = []
            self.printt('poly_buy_mini_price 기준초과 진입')
            cross_winner_cell = 1004
            self.printt(cross_winner_cell)
            sOrgOrdNo_cell = ''
            for have in range(len(stock_tarket_item_list)):
                for i in range(len(self.stock_item_data['stock_item_no'])):
                    if stock_tarket_item_list[have] == self.stock_item_data['stock_item_no'][i]:
                        # 매수건수 체크
                        market_in_cnt = self.market_in_buy_cnt(stock_tarket_item_list[have], buy_able_money)
                        # 매수건수 0이상이면
                        if market_in_cnt > 0:
                            # 매수종목 추가시 가능금액 차감
                            buy_able_money -= self.market_in_percent_won
                            # 구분 / 매수수량 / 종목코드 / 원주문번호
                            cross_winner.append(cross_winner_cell)
                            volume_listed_var.append(market_in_cnt)
                            item_list.append(stock_tarket_item_list[have])
                            sOrgOrdNo.append(sOrgOrdNo_cell)
            self.printt('poly_buy_mini_price 기준초과 item_list')
            self.printt(volume_listed_var)
            self.printt(item_list)
            # 선물 변화 건수 체크
            future_s_change_cnt = len(self.future_s_change_listed_var)
            if future_s_change_cnt >= 1:
                # 자동주문 버튼 True 주문실행
                if self.auto_order_button_var == True:
                    # 주문준비 완료
                    self.order_ready_stock(cross_winner, volume_listed_var, item_list, sOrgOrdNo)

    # 매수 건수 체크
    def market_in_buy_cnt(self, buy_item_list, buy_able_money):
        for i in range(len(self.stock_item_data['stock_item_no'])):
            if buy_item_list == self.stock_item_data['stock_item_no'][i]:
                # 주문가능 금액 < self.market_in_percent_won
                if buy_able_money < self.market_in_percent_won:
                    buy_market_in_cnt_int = 0
                    self.printt('buy_able_money < self.market_in_percent_won')
                    self.printt(buy_market_in_cnt_int)
                    return buy_market_in_cnt_int
                else:
                    buy_market_in_cnt_int = int(math.floor(self.market_in_percent_won / self.stock_item_data['stock_end'][i]))
                    # 매수가능 건수
                    if buy_market_in_cnt_int == 0:
                        buy_market_in_cnt_int = 0
                        self.printt('buy_market_in_cnt_int = 0')
                        self.printt(buy_market_in_cnt_int)
                        return buy_market_in_cnt_int
                    elif buy_market_in_cnt_int > 0:
                        # self.printt('buy_market_in_cnt')
                        # self.printt(buy_market_in_cnt)
                        # self.printt(buy_market_in_cnt_int)
                        return buy_market_in_cnt_int
        return 0






























































    # 비교변수 초기 바인딩(slow)
    def slow_cmp_var_reset(self):
        # 초기화 먼저
        self.slow_cmp_call = {'2': [], '1': [], '0': [], '-1': [], '-2': []}
        self.slow_cmp_put = {'2': [], '1': [], '0': [], '-1': [], '-2': []}

        # 비교변수 초기값 :: 각 컬럼당 2개씩 바인딩 range(0, 2):
        for i in range(0, 2):
            self.slow_cmp_call['2'].append(self.output_call_option_data['run_price'][self.center_index + Up2_CenterOption_Down2])
            self.slow_cmp_call['1'].append(self.output_call_option_data['run_price'][self.center_index + Up2_CenterOption_Down2 - 1])
            self.slow_cmp_call['0'].append(self.output_call_option_data['run_price'][self.center_index + Up2_CenterOption_Down2 - 2])
            self.slow_cmp_call['-1'].append(self.output_call_option_data['run_price'][self.center_index - Up2_CenterOption_Down2 + 1])
            self.slow_cmp_call['-2'].append(self.output_call_option_data['run_price'][self.center_index - Up2_CenterOption_Down2])

            self.slow_cmp_put['2'].append(self.output_put_option_data['run_price'][self.center_index - Up2_CenterOption_Down2])
            self.slow_cmp_put['1'].append(self.output_put_option_data['run_price'][self.center_index - Up2_CenterOption_Down2 + 1])
            self.slow_cmp_put['0'].append(self.output_put_option_data['run_price'][self.center_index + Up2_CenterOption_Down2 - 2])
            self.slow_cmp_put['-1'].append(self.output_put_option_data['run_price'][self.center_index + Up2_CenterOption_Down2 - 1])
            self.slow_cmp_put['-2'].append(self.output_put_option_data['run_price'][self.center_index + Up2_CenterOption_Down2])

    # timer1sec Cross_check
    def slow_cross_check_shift(self):
        # 비교변수 쉬프트
        # self.slow_cmp_call = {'2': [], '1': [], '0': [], '-1': [], '-2': []}
        # self.slow_cmp_put = {'2': [], '1': [], '0': [], '-1': [], '-2': []}
        for i in range(self.center_index - Up2_CenterOption_Down2, self.center_index + Up2_CenterOption_Down2 + 1):
            # i - self.center_index 콜(-)
            up_down_index = i - self.center_index
            up_down_index_str = str(up_down_index)
            del self.slow_cmp_call[up_down_index_str][-2]
            self.slow_cmp_call[up_down_index_str].append(self.output_call_option_data['run_price'][i])
            # print(self.slow_cmp_call)
            # self.center_index - i 풋(+)
            up_down_index = self.center_index - i
            up_down_index_str = str(up_down_index)
            del self.slow_cmp_put[up_down_index_str][-2]
            self.slow_cmp_put[up_down_index_str].append(self.output_put_option_data['run_price'][i])
            # print(self.slow_cmp_put)

    # cross_check_trans
    def slow_cross_check_trans(self):
        # self.slow_cross_check_var = {'up2': [0], 'up1': [0], 'zero': [0], 'dn1': [0], 'dn2': [0],
        # 'up2_c_d': [0], 'up1_c_d': [0], 'dn1_c_d': [0], 'dn2_c_d': [0],
        # 'up2_p_d': [0], 'up1_p_d': [0], 'dn1_p_d': [0], 'dn2_p_d': [0]}

        # self.slow_cross_check_var = {'up2': [0], 'up1': [0], 'zero': [0], 'dn1': [0], 'dn2': [0],
        # cross = Cross(self.slow_cmp_call['2'], self.slow_cmp_put['2'])
        # cross_check_ret = cross.cross_check()
        # if cross_check_ret != None:
        #     self.slow_cross_check_var['up2'].append(cross_check_ret)
        #
        #     # 크로스 체크 결과
        #     self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['1'], self.slow_cmp_put['1'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['up1'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['0'], self.slow_cmp_put['0'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['zero'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['-1'], self.slow_cmp_put['-1'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['dn1'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        # cross = Cross(self.slow_cmp_call['-2'], self.slow_cmp_put['-2'])
        # cross_check_ret = cross.cross_check()
        # if cross_check_ret != None:
        #     self.slow_cross_check_var['dn2'].append(cross_check_ret)
        #
        #     # 크로스 체크 결과
        #     self.slow_cross_check_result(self.slow_cross_check_var)

        # 'up2_c_d': [0], 'up1_c_d': [0], 'dn1_c_d': [0], 'dn2_c_d': [0],
        cross = Cross(self.slow_cmp_call['1'], self.slow_cmp_put['2'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['up2_c_d'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['0'], self.slow_cmp_put['1'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['up1_c_d'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['-1'], self.slow_cmp_put['0'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['dn1_c_d'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['-2'], self.slow_cmp_put['-1'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['dn2_c_d'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        # 'up2_p_d': [0], 'up1_p_d': [0], 'dn1_p_d': [0], 'dn2_p_d': [0]}
        cross = Cross(self.slow_cmp_call['-1'], self.slow_cmp_put['-2'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['dn2_p_d'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['0'], self.slow_cmp_put['-1'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['dn1_p_d'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['1'], self.slow_cmp_put['0'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['up1_p_d'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

        cross = Cross(self.slow_cmp_call['2'], self.slow_cmp_put['1'])
        cross_check_ret = cross.cross_check()
        if cross_check_ret != None:
            self.slow_cross_check_var['up2_p_d'].append(cross_check_ret)

            # 크로스 체크 결과
            self.slow_cross_check_result(self.slow_cross_check_var)

    # 교차 변수 이동
    def slow_cross_check_result(self, slow_cross_check_var):
        # self.printt('slow_cross_check_var')
        # self.printt(slow_cross_check_var)

        # 'up2_c_d': [0], 'up1_c_d': [0], 'dn1_c_d': [0], 'dn2_c_d': [0],
        # 중심가 변경 완결시점(상하 2개씩 만족하면)
        # if slow_cross_check_var['up2_c_d'][-1] == 2:
        #     if slow_cross_check_var['up1_c_d'][-1] == 2:
        if slow_cross_check_var['dn1_c_d'][-1] == 2:
            if slow_cross_check_var['dn2_c_d'][-1] == 2:
                # slow_cross_check_var 중심가 변경 쉬프트
                self.slow_cross_check_var['up2_p_d'][-1] = self.slow_cross_check_var['up2_c_d'][-1]
                self.slow_cross_check_var['up1_p_d'][-1] = self.slow_cross_check_var['up1_c_d'][-1]
                self.slow_cross_check_var['dn1_p_d'][-1] = self.slow_cross_check_var['dn1_c_d'][-1]
                self.slow_cross_check_var['dn2_p_d'][-1] = self.slow_cross_check_var['dn2_c_d'][-1]
                # slow cross check double reset
                self.slow_cross_check_var['up2_c_d'][-1] = 0
                self.slow_cross_check_var['up1_c_d'][-1] = 0
                self.slow_cross_check_var['dn1_c_d'][-1] = 0
                self.slow_cross_check_var['dn2_c_d'][-1] = 0
                # 중심가 변경시 4/5/6도 함께 초기화
                self.slow_cross_check_var['up1'][-1] = 0
                self.slow_cross_check_var['zero'][-1] = 0
                self.slow_cross_check_var['dn1'][-1] = 0

        # 'up2_p_d': [0], 'up1_p_d': [0], 'dn1_p_d': [0], 'dn2_p_d': [0]}
        # 중심가 변경 완결시점(상하 2개씩 만족하면)
        # if slow_cross_check_var['dn2_p_d'][-1] == 3:
        #     if slow_cross_check_var['dn1_p_d'][-1] == 3:
        if slow_cross_check_var['up2_p_d'][-1] == 3:
            if slow_cross_check_var['up1_p_d'][-1] == 3:
                # slow_cross_check_var 중심가 변경 쉬프트
                self.slow_cross_check_var['up2_c_d'][-1] = self.slow_cross_check_var['up2_p_d'][-1]
                self.slow_cross_check_var['up1_c_d'][-1] = self.slow_cross_check_var['up1_p_d'][-1]
                self.slow_cross_check_var['dn1_c_d'][-1] = self.slow_cross_check_var['dn1_p_d'][-1]
                self.slow_cross_check_var['dn2_c_d'][-1] = self.slow_cross_check_var['dn2_p_d'][-1]
                # slow cross check double reset
                self.slow_cross_check_var['up2_p_d'][-1] = 0
                self.slow_cross_check_var['up1_p_d'][-1] = 0
                self.slow_cross_check_var['dn1_p_d'][-1] = 0
                self.slow_cross_check_var['dn2_p_d'][-1] = 0
                # 중심가 변경시 4/5/6도 함께 초기화
                self.slow_cross_check_var['up1'][-1] = 0
                self.slow_cross_check_var['zero'][-1] = 0
                self.slow_cross_check_var['dn1'][-1] = 0

    # money_option_point_ch
    def money_option_point_ch(self, money_won):
        money_point = money_won / Option_Mul_Money
        return money_point

    # 옵션 종목검색(매수)
    def option_s_buy_items_search(self, myhave_total_future_s_cnt, option_s_hedge_ratio, put_or_call, month_mall_type):

        # -----
        # option_s_sell_items_search
        # 위의 함수 복사만 해놓은 상태 - 아직 작업은 않했음(혹시 옵션 헤지 매수 할때를 위하여)
        # -----

        # -----
        # 옵션 임시재고
        option_s_myhave_temp = {'code': [], 'myhave_cnt': [], 'sell_or_buy': []}
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 목표치
        item_list_cnt_tarket = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 최종 결과
        item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 현재 선물의 델타를 건수 * option_s_hedge_ratio 곱해서 절대값 구하고
        myhave_future_s_delta_sum = abs(myhave_total_future_s_cnt * option_s_hedge_ratio)
        myhave_option_s_delta = 0
        # -----


    # 옵션 종목검색(매도)
    def option_s_sell_items_search(self, myhave_total_future_s_cnt, option_s_hedge_ratio, put_or_call, month_mall_type):
        # -----
        # 옵션 임시재고
        option_s_myhave_temp = {'code': [], 'myhave_cnt': [], 'sell_or_buy': []}
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 목표치
        item_list_cnt_tarket = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 최종 결과
        item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 현재 선물의 델타를 건수 * option_s_hedge_ratio 곱해서 절대값 구하고
        myhave_future_s_delta_sum = abs(myhave_total_future_s_cnt * option_s_hedge_ratio)
        myhave_option_s_delta = 0
        # -----

        # -----
        # 옵션의 델타를 중심가 기준으로 50 => 30 => 10 으로 정의하고
        # 중심가 찾는것을 델타기준으로 하면서 중심가는 오로지 종목코드 가져오는 용도로
        call_option_delta_center_2 = 10
        call_option_delta_center_1 = 30

        put_option_delta_center_1 = 30
        put_option_delta_center_2 = 10

        # 현재 옵션의 델타를 먼저 체크
        # 당월물
        if month_mall_type == 'center_index':
            # 콜
            # 만일 정의한 델타보다 현재의 델타값이 크면
            if call_option_delta_center_2 < abs(float(self.output_call_option_data['Delta'][self.center_index - 2])):
                call_option_delta_center_2 = abs(float(self.output_call_option_data['Delta'][self.center_index - 2]))
            if call_option_delta_center_1 < abs(float(self.output_call_option_data['Delta'][self.center_index - 1])):
                call_option_delta_center_1 = abs(float(self.output_call_option_data['Delta'][self.center_index - 1]))
            # 풋
            # 만일 정의한 델타보다 현재의 델타값이 크면
            if put_option_delta_center_1 < abs(float(self.output_put_option_data['Delta'][self.center_index + 1])):
                put_option_delta_center_1 = abs(float(self.output_put_option_data['Delta'][self.center_index + 1]))
            if put_option_delta_center_2 < abs(float(self.output_put_option_data['Delta'][self.center_index + 2])):
                put_option_delta_center_2 = abs(float(self.output_put_option_data['Delta'][self.center_index + 2]))
        # 차월물
        elif month_mall_type == 'center_index_45':
            # 콜
            # 만일 정의한 델타보다 현재의 델타값이 크면
            if call_option_delta_center_2 < abs(float(self.output_call_option_data_45['Delta'][self.center_index_45 - 2])):
                call_option_delta_center_2 = abs(float(self.output_call_option_data_45['Delta'][self.center_index_45 - 2]))
            if call_option_delta_center_1 < abs(float(self.output_call_option_data_45['Delta'][self.center_index_45 - 1])):
                call_option_delta_center_1 = abs(float(self.output_call_option_data_45['Delta'][self.center_index_45 - 1]))
            # 풋
            # 만일 정의한 델타보다 현재의 델타값이 크면
            if put_option_delta_center_1 < abs(float(self.output_put_option_data_45['Delta'][self.center_index_45 + 1])):
                put_option_delta_center_1 = abs(float(self.output_put_option_data_45['Delta'][self.center_index_45 + 1]))
            if put_option_delta_center_2 < abs(float(self.output_put_option_data_45['Delta'][self.center_index_45 + 2])):
                put_option_delta_center_2 = abs(float(self.output_put_option_data_45['Delta'][self.center_index_45 + 2]))
        # -----

        # 선물매도(풋매도 헷징)
        # put
        if put_or_call == 'put':
            # 당월물
            if month_mall_type == 'center_index':
                # self.center_index

                # -----
                # 옵션 행사가와 비교하여 옵션매도주문증거금 구하기
                for d in range(len(self.option_s_sell_deposit_money_data['option_price'])):
                    if self.option_s_sell_deposit_money_data['option_price'][d] == \
                            self.output_put_option_data['option_price'][self.center_index + 1]:
                        # 옵션매도주문증거금
                        self.option_s_sell_order_deposit_money = \
                            self.option_s_sell_deposit_money_data['put_sell_order_deposit_money'][d]
                        self.printt('self.option_s_sell_order_deposit_money(put/center_index)')
                        self.printt(format(self.option_s_sell_order_deposit_money, ','))
                # -----

                # -----
                # 옵션 재고의 'Delta' 구하기
                # 중심가 기준으로 +-n까지 보유 옵션 델타 구하기
                for mh in range(len(self.option_myhave['code'])):
                    # 풋이므로 +
                    # 당월물
                    for op in range(self.center_index + 2, self.center_index, -1):
                        if self.option_myhave['code'][mh][:3] == '301':
                            if self.option_myhave['sell_or_buy'][mh] == 1:
                                if self.option_myhave['code'][mh] == self.output_put_option_data['code'][op]:
                                    if op == (self.center_index + 2):
                                        myhave_option_s_delta += self.option_myhave['myhave_cnt'][mh] * put_option_delta_center_2
                                    elif op == (self.center_index + 1):
                                        myhave_option_s_delta += self.option_myhave['myhave_cnt'][mh] * put_option_delta_center_1
                                    # 옵션의 델타를 구하면서 임시재고 목록과 건수 추가
                                    option_s_myhave_temp['code'].append(self.option_myhave['code'][mh])
                                    option_s_myhave_temp['myhave_cnt'].append(self.option_myhave['myhave_cnt'][mh])
                                    option_s_myhave_temp['sell_or_buy'].append(self.option_myhave['sell_or_buy'][mh])
                # print(myhave_option_s_delta)
                # print(option_s_myhave_temp)
                # -----

                # 선물의 델타가 옵션의 델타보다 클때 [옵션 추가 매도]
                if myhave_future_s_delta_sum > myhave_option_s_delta:
                    # 델타의 차이를 구하고
                    myhave_option_s_delta_diff = myhave_future_s_delta_sum - myhave_option_s_delta
                    # 중심가 다음 옵션의 델타값을 구해서
                    center_index_1_delta = put_option_delta_center_1
                    # 추가진입 건수를 구한 다음
                    sell_tarket_cnt = math.floor(myhave_option_s_delta_diff / center_index_1_delta)
                    # 추가진입 건수가 0일때는 제외
                    if sell_tarket_cnt > 0:
                        # 종목검색 리스트에 매도 추가한다
                        item_list_cnt['code_no'].append(self.output_put_option_data['code'][self.center_index + 1])
                        item_list_cnt['cnt'].append(sell_tarket_cnt)
                        item_list_cnt['sell_buy_type'].append(1)
                    # print(item_list_cnt)
                # 옵션의 델타가 선물의 델타보다 클때 [옵션 청산 매수]
                elif myhave_future_s_delta_sum < myhave_option_s_delta:
                    # 델타의 차이를 구하고
                    myhave_option_s_delta_diff = myhave_option_s_delta - myhave_future_s_delta_sum
                    # 옵션과 선물의 델타 차이를 비교하여 청산(매수)옵션의 델타보가 클때만 [풋이므로 +] ::중심가 위아래 돌리는 값으로
                    if myhave_option_s_delta_diff > put_option_delta_center_2:
                        # 풋이므로 중심가 아래에서 n번째 부터 꺼꾸로
                        for op in range(self.center_index + 2, self.center_index, -1):
                            # 전체 보유 옵션을 돌리고
                            for mh in range(len(self.option_myhave['code'])):
                                # 풋일때만
                                if self.option_myhave['code'][mh][:3] == '301':
                                    # 매도일때만
                                    if self.option_myhave['sell_or_buy'][mh] == 1:
                                        # 보유 옵션과 종목코드 비교하여
                                        if self.option_myhave['code'][mh] == self.output_put_option_data['code'][op]:
                                            # 해당종목 보유 건수만큼 돌리면서 매수처리
                                            for cnt in range(self.option_myhave['myhave_cnt'][mh]):
                                                if myhave_future_s_delta_sum == myhave_option_s_delta:
                                                    break
                                                elif myhave_future_s_delta_sum > myhave_option_s_delta:
                                                    break
                                                elif myhave_future_s_delta_sum < myhave_option_s_delta:
                                                    # # 종목검색 리스트에 보유종목의 매수 추가
                                                    # item_list_cnt['code_no'].append(self.option_myhave['code'][mh])
                                                    # item_list_cnt['cnt'].append(1)
                                                    # item_list_cnt['sell_buy_type'].append(2)
                                                    # 매수추가 했으므로 델타 빼주고
                                                    if op == (self.center_index + 2):
                                                        myhave_option_s_delta -= put_option_delta_center_2
                                                    elif op == (self.center_index + 1):
                                                        myhave_option_s_delta -= put_option_delta_center_1
                                                    # 옵션 임시재고에서도 빼주고
                                                    for ot in range(len(option_s_myhave_temp['code'])):
                                                        if option_s_myhave_temp['code'][ot] == self.option_myhave['code'][mh]:
                                                            option_s_myhave_temp['myhave_cnt'][ot] -= 1
                                                            # 만일 myhave_cnt 0이라면
                                                            # 리스트에서 삭제
                                                            if option_s_myhave_temp['myhave_cnt'][ot] == 0:
                                                                del option_s_myhave_temp['code'][ot]
                                                                del option_s_myhave_temp['myhave_cnt'][ot]
                                                                del option_s_myhave_temp['sell_or_buy'][ot]
                                                                self.printt('#  옵션 임시재고에서도 빼주고 만일 myhave_cnt 0이라면 리스트에서 삭제')
                                                                break  # 리스트 요소를 삭제하였으므로 for문 중지
                # print(myhave_option_s_delta)
                # print(option_s_myhave_temp)

            # 차월물
            elif month_mall_type == 'center_index_45':
                # self.center_index_45

                # -----
                # 옵션 행사가와 비교하여 옵션매도주문증거금 구하기
                for d in range(len(self.option_s_sell_deposit_money_data['option_price'])):
                    if self.option_s_sell_deposit_money_data['option_price'][d] == \
                            self.output_put_option_data_45['option_price'][self.center_index_45 + 1]:
                        # 옵션매도주문증거금
                        self.option_s_sell_order_deposit_money = \
                            self.option_s_sell_deposit_money_data['put_sell_order_deposit_money'][d]
                        self.printt('self.option_s_sell_order_deposit_money(put/center_index_45)')
                        self.printt(format(self.option_s_sell_order_deposit_money, ','))
                # -----

                # -----
                # 옵션 재고의 'Delta' 구하기
                # 중심가 기준으로 +-n까지 보유 옵션 델타 구하기
                # 풋이므로 +
                # 차월물
                for op in range(self.center_index_45 + 2, self.center_index_45, -1):
                    for mh in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][mh][:3] == '301':
                            if self.option_myhave['sell_or_buy'][mh] == 1:
                                if self.option_myhave['code'][mh] == self.output_put_option_data_45['code'][op]:
                                    if op == (self.center_index_45 + 2):
                                        myhave_option_s_delta += self.option_myhave['myhave_cnt'][
                                                                     mh] * put_option_delta_center_2
                                    elif op == (self.center_index_45 + 1):
                                        myhave_option_s_delta += self.option_myhave['myhave_cnt'][
                                                                     mh] * put_option_delta_center_1
                                    # 옵션의 델타를 구하면서 임시재고 목록과 건수 추가
                                    option_s_myhave_temp['code'].append(self.option_myhave['code'][mh])
                                    option_s_myhave_temp['myhave_cnt'].append(self.option_myhave['myhave_cnt'][mh])
                                    option_s_myhave_temp['sell_or_buy'].append(self.option_myhave['sell_or_buy'][mh])
                # print(myhave_option_s_delta)
                # print(option_s_myhave_temp)
                # -----

                # 선물의 델타가 옵션의 델타보다 클때 [옵션 추가 매도]
                if myhave_future_s_delta_sum > myhave_option_s_delta:
                    # 델타의 차이를 구하고
                    myhave_option_s_delta_diff = myhave_future_s_delta_sum - myhave_option_s_delta
                    # 중심가 다음 옵션의 델타값을 구해서
                    center_index_1_delta = put_option_delta_center_1
                    # 추가진입 건수를 구한 다음
                    sell_tarket_cnt = math.floor(myhave_option_s_delta_diff / center_index_1_delta)
                    # 추가진입 건수가 0일때는 제외
                    if sell_tarket_cnt > 0:
                        # 종목검색 리스트에 매도 추가한다
                        item_list_cnt['code_no'].append(self.output_put_option_data_45['code'][self.center_index_45 + 1])
                        item_list_cnt['cnt'].append(sell_tarket_cnt)
                        item_list_cnt['sell_buy_type'].append(1)
                    # print(item_list_cnt)
                # 옵션의 델타가 선물의 델타보다 클때 [옵션 청산 매수]
                elif myhave_future_s_delta_sum < myhave_option_s_delta:
                    # 델타의 차이를 구하고
                    myhave_option_s_delta_diff = myhave_option_s_delta - myhave_future_s_delta_sum
                    # 옵션과 선물의 델타 차이를 비교하여 청산(매수)옵션의 델타보가 클때만 [풋이므로 +] ::중심가 위아래 돌리는 값으로
                    if myhave_option_s_delta_diff > put_option_delta_center_2:
                        # 풋이므로 중심가 아래에서 n번째 부터 꺼꾸로
                        for op in range(self.center_index_45 + 2, self.center_index_45, -1):
                            # 전체 보유 옵션을 돌리고
                            for mh in range(len(self.option_myhave['code'])):
                                # 풋일때만
                                if self.option_myhave['code'][mh][:3] == '301':
                                    # 매도일때만
                                    if self.option_myhave['sell_or_buy'][mh] == 1:
                                        # 보유 옵션과 종목코드 비교하여
                                        if self.option_myhave['code'][mh] == self.output_put_option_data_45['code'][op]:
                                            # 해당종목 보유 건수만큼 돌리면서 매수처리
                                            for cnt in range(self.option_myhave['myhave_cnt'][mh]):
                                                if myhave_future_s_delta_sum == myhave_option_s_delta:
                                                    break
                                                elif myhave_future_s_delta_sum > myhave_option_s_delta:
                                                    break
                                                elif myhave_future_s_delta_sum < myhave_option_s_delta:
                                                    # # 종목검색 리스트에 보유종목의 매수 추가
                                                    # item_list_cnt['code_no'].append(self.option_myhave['code'][mh])
                                                    # item_list_cnt['cnt'].append(1)
                                                    # item_list_cnt['sell_buy_type'].append(2)
                                                    # 매수추가 했으므로 델타 빼주고
                                                    if op == (self.center_index_45 + 2):
                                                        myhave_option_s_delta -= put_option_delta_center_2
                                                    elif op == (self.center_index_45 + 1):
                                                        myhave_option_s_delta -= put_option_delta_center_1
                                                    # 옵션 임시재고에서도 빼주고
                                                    for ot in range(len(option_s_myhave_temp['code'])):
                                                        if option_s_myhave_temp['code'][ot] == \
                                                                self.option_myhave['code'][mh]:
                                                            option_s_myhave_temp['myhave_cnt'][ot] -= 1
                                                            # 만일 myhave_cnt 0이라면
                                                            # 리스트에서 삭제
                                                            if option_s_myhave_temp['myhave_cnt'][ot] == 0:
                                                                del option_s_myhave_temp['code'][ot]
                                                                del option_s_myhave_temp['myhave_cnt'][ot]
                                                                del option_s_myhave_temp['sell_or_buy'][ot]
                                                                self.printt(
                                                                    '#  옵션 임시재고에서도 빼주고 만일 myhave_cnt 0이라면 리스트에서 삭제')
                                                                break  # 리스트 요소를 삭제하였으므로 for문 중지
                # print(myhave_option_s_delta)
                # print(option_s_myhave_temp)

        # 선물매수(콜매도 헷징)
        # call
        elif put_or_call == 'call':
            # 당월물
            if month_mall_type == 'center_index':
                # self.center_index

                # -----
                # 옵션 행사가와 비교하여 옵션매도주문증거금 구하기
                for d in range(len(self.option_s_sell_deposit_money_data['option_price'])):
                    if self.option_s_sell_deposit_money_data['option_price'][d] == \
                            self.output_call_option_data['option_price'][self.center_index - 1]:
                        # 옵션매도주문증거금
                        self.option_s_sell_order_deposit_money = \
                            self.option_s_sell_deposit_money_data['call_sell_order_deposit_money'][d]
                        self.printt('self.option_s_sell_order_deposit_money(call/center_index)')
                        self.printt(format(self.option_s_sell_order_deposit_money, ','))
                # -----

                # -----
                # 옵션 재고의 'Delta' 구하기
                # 중심가 기준으로 +-n까지 보유 옵션 델타 구하기
                for mh in range(len(self.option_myhave['code'])):
                    # 콜이므로 -+
                    # 당월물
                    for op in range(self.center_index - 2, self.center_index, +1):
                        if self.option_myhave['code'][mh][:3] == '201':
                            if self.option_myhave['sell_or_buy'][mh] == 1:
                                if self.option_myhave['code'][mh] == self.output_call_option_data['code'][op]:
                                    if op == (self.center_index - 2):
                                        myhave_option_s_delta += self.option_myhave['myhave_cnt'][
                                                                     mh] * call_option_delta_center_2
                                    elif op == (self.center_index - 1):
                                        myhave_option_s_delta += self.option_myhave['myhave_cnt'][
                                                                     mh] * call_option_delta_center_1
                                    # 옵션의 델타를 구하면서 임시재고 목록과 건수 추가
                                    option_s_myhave_temp['code'].append(self.option_myhave['code'][mh])
                                    option_s_myhave_temp['myhave_cnt'].append(self.option_myhave['myhave_cnt'][mh])
                                    option_s_myhave_temp['sell_or_buy'].append(self.option_myhave['sell_or_buy'][mh])
                # print(myhave_option_s_delta)
                # print(option_s_myhave_temp)
                # -----

                # 선물의 델타가 옵션의 델타보다 클때 [옵션 추가 매도]
                if myhave_future_s_delta_sum > myhave_option_s_delta:
                    # 델타의 차이를 구하고
                    myhave_option_s_delta_diff = myhave_future_s_delta_sum - myhave_option_s_delta
                    # 중심가 다음 옵션의 델타값을 구해서
                    center_index_1_delta = call_option_delta_center_1
                    # 추가진입 건수를 구한 다음
                    sell_tarket_cnt = math.floor(myhave_option_s_delta_diff / center_index_1_delta)
                    # 추가진입 건수가 0일때는 제외
                    if sell_tarket_cnt > 0:
                        # 종목검색 리스트에 매도 추가한다
                        item_list_cnt['code_no'].append(self.output_call_option_data['code'][self.center_index - 1])
                        item_list_cnt['cnt'].append(sell_tarket_cnt)
                        item_list_cnt['sell_buy_type'].append(1)
                    # print(item_list_cnt)
                # 옵션의 델타가 선물의 델타보다 클때 [옵션 청산 매수]
                elif myhave_future_s_delta_sum < myhave_option_s_delta:
                    # 델타의 차이를 구하고
                    myhave_option_s_delta_diff = myhave_option_s_delta - myhave_future_s_delta_sum
                    # 옵션과 선물의 델타 차이를 비교하여 청산(매수)옵션의 델타보가 클때만 [콜이므로 -] ::중심가 위아래 돌리는 값으로
                    if myhave_option_s_delta_diff > call_option_delta_center_2:
                        # 콜이므로 중심가 위로부터
                        for op in range(self.center_index - 2, self.center_index, +1):
                            # 전체 보유 옵션을 돌리고
                            for mh in range(len(self.option_myhave['code'])):
                                # 풋일때만
                                if self.option_myhave['code'][mh][:3] == '201':
                                    # 매도일때만
                                    if self.option_myhave['sell_or_buy'][mh] == 1:
                                        # 보유 옵션과 종목코드 비교하여
                                        if self.option_myhave['code'][mh] == self.output_call_option_data['code'][op]:
                                            # 해당종목 보유 건수만큼 돌리면서 매수처리
                                            for cnt in range(self.option_myhave['myhave_cnt'][mh]):
                                                if myhave_future_s_delta_sum == myhave_option_s_delta:
                                                    break
                                                elif myhave_future_s_delta_sum > myhave_option_s_delta:
                                                    break
                                                elif myhave_future_s_delta_sum < myhave_option_s_delta:
                                                    # # 종목검색 리스트에 보유종목의 매수 추가
                                                    # item_list_cnt['code_no'].append(self.option_myhave['code'][mh])
                                                    # item_list_cnt['cnt'].append(1)
                                                    # item_list_cnt['sell_buy_type'].append(2)
                                                    # 매수추가 했으므로 델타 빼주고
                                                    if op == (self.center_index - 2):
                                                        myhave_option_s_delta -= call_option_delta_center_2
                                                    elif op == (self.center_index - 1):
                                                        myhave_option_s_delta -= call_option_delta_center_1
                                                    # 옵션 임시재고에서도 빼주고
                                                    for ot in range(len(option_s_myhave_temp['code'])):
                                                        if option_s_myhave_temp['code'][ot] == \
                                                                self.option_myhave['code'][mh]:
                                                            option_s_myhave_temp['myhave_cnt'][ot] -= 1
                                                            # 만일 myhave_cnt 0이라면
                                                            # 리스트에서 삭제
                                                            if option_s_myhave_temp['myhave_cnt'][ot] == 0:
                                                                del option_s_myhave_temp['code'][ot]
                                                                del option_s_myhave_temp['myhave_cnt'][ot]
                                                                del option_s_myhave_temp['sell_or_buy'][ot]
                                                                self.printt(
                                                                    '#  옵션 임시재고에서도 빼주고 만일 myhave_cnt 0이라면 리스트에서 삭제')
                                                                break  # 리스트 요소를 삭제하였으므로 for문 중지
                # print(myhave_option_s_delta)
                # print(option_s_myhave_temp)

            # 차월물
            elif month_mall_type == 'center_index_45':
                # self.center_index_45

                # -----
                # 옵션 행사가와 비교하여 옵션매도주문증거금 구하기
                for d in range(len(self.option_s_sell_deposit_money_data['option_price'])):
                    if self.option_s_sell_deposit_money_data['option_price'][d] == \
                            self.output_call_option_data_45['option_price'][self.center_index_45 - 1]:
                        # 옵션매도주문증거금
                        self.option_s_sell_order_deposit_money = \
                            self.option_s_sell_deposit_money_data['call_sell_order_deposit_money'][d]
                        self.printt('self.option_s_sell_order_deposit_money(call/center_index_45)')
                        self.printt(format(self.option_s_sell_order_deposit_money, ','))
                # -----

                # -----
                # 옵션 재고의 'Delta' 구하기
                # 중심가 기준으로 +-n까지 보유 옵션 델타 구하기
                for mh in range(len(self.option_myhave['code'])):
                    # 콜이므로 -+
                    # 차월물
                    for op in range(self.center_index_45 - 2, self.center_index_45, +1):
                        if self.option_myhave['code'][mh][:3] == '201':
                            if self.option_myhave['sell_or_buy'][mh] == 1:
                                if self.option_myhave['code'][mh] == self.output_call_option_data_45['code'][op]:
                                    if op == (self.center_index_45 - 2):
                                        myhave_option_s_delta += self.option_myhave['myhave_cnt'][
                                                                     mh] * call_option_delta_center_2
                                    elif op == (self.center_index_45 - 1):
                                        myhave_option_s_delta += self.option_myhave['myhave_cnt'][
                                                                     mh] * call_option_delta_center_1
                                    # 옵션의 델타를 구하면서 임시재고 목록과 건수 추가
                                    option_s_myhave_temp['code'].append(self.option_myhave['code'][mh])
                                    option_s_myhave_temp['myhave_cnt'].append(self.option_myhave['myhave_cnt'][mh])
                                    option_s_myhave_temp['sell_or_buy'].append(self.option_myhave['sell_or_buy'][mh])
                # print(myhave_option_s_delta)
                # print(option_s_myhave_temp)
                # -----

                # 선물의 델타가 옵션의 델타보다 클때 [옵션 추가 매도]
                if myhave_future_s_delta_sum > myhave_option_s_delta:
                    # 델타의 차이를 구하고
                    myhave_option_s_delta_diff = myhave_future_s_delta_sum - myhave_option_s_delta
                    # 중심가 다음 옵션의 델타값을 구해서
                    center_index_1_delta = call_option_delta_center_1
                    # 추가진입 건수를 구한 다음
                    sell_tarket_cnt = math.floor(myhave_option_s_delta_diff / center_index_1_delta)
                    # 종목검색 리스트에 매도 추가한다
                    # 추가진입 건수가 0일때는 제외
                    if sell_tarket_cnt > 0:
                        item_list_cnt['code_no'].append(self.output_call_option_data_45['code'][self.center_index_45 - 1])
                        item_list_cnt['cnt'].append(sell_tarket_cnt)
                        item_list_cnt['sell_buy_type'].append(1)
                    # print(item_list_cnt)
                # 옵션의 델타가 선물의 델타보다 클때 [옵션 청산 매수]
                elif myhave_future_s_delta_sum < myhave_option_s_delta:
                    # 델타의 차이를 구하고
                    myhave_option_s_delta_diff = myhave_option_s_delta - myhave_future_s_delta_sum
                    # 옵션과 선물의 델타 차이를 비교하여 청산(매수)옵션의 델타보가 클때만 [콜이므로 -] ::중심가 위아래 돌리는 값으로
                    if myhave_option_s_delta_diff > call_option_delta_center_2:
                        # 콜이므로 중심가 위로 3번째
                        for op in range(self.center_index_45 - 2, self.center_index_45, 1):
                            # 전체 보유 옵션을 돌리고
                            for mh in range(len(self.option_myhave['code'])):
                                # 풋일때만
                                if self.option_myhave['code'][mh][:3] == '201':
                                    # 매도일때만
                                    if self.option_myhave['sell_or_buy'][mh] == 1:
                                        # 보유 옵션과 종목코드 비교하여
                                        if self.option_myhave['code'][mh] == self.output_call_option_data_45['code'][op]:
                                            # 해당종목 보유 건수만큼 돌리면서 매수처리
                                            for cnt in range(self.option_myhave['myhave_cnt'][mh]):
                                                if myhave_future_s_delta_sum == myhave_option_s_delta:
                                                    break
                                                elif myhave_future_s_delta_sum > myhave_option_s_delta:
                                                    break
                                                elif myhave_future_s_delta_sum < myhave_option_s_delta:
                                                    # # 종목검색 리스트에 보유종목의 매수 추가
                                                    # item_list_cnt['code_no'].append(self.option_myhave['code'][mh])
                                                    # item_list_cnt['cnt'].append(1)
                                                    # item_list_cnt['sell_buy_type'].append(2)
                                                    # 매수추가 했으므로 델타 빼주고
                                                    if op == (self.center_index_45 - 2):
                                                        myhave_option_s_delta -= call_option_delta_center_2
                                                    elif op == (self.center_index_45 - 1):
                                                        myhave_option_s_delta -= call_option_delta_center_1
                                                    # 옵션 임시재고에서도 빼주고
                                                    for ot in range(len(option_s_myhave_temp['code'])):
                                                        if option_s_myhave_temp['code'][ot] == self.option_myhave['code'][mh]:
                                                            option_s_myhave_temp['myhave_cnt'][ot] -= 1
                                                            # 만일 myhave_cnt 0이라면
                                                            # 리스트에서 삭제
                                                            if option_s_myhave_temp['myhave_cnt'][ot] == 0:
                                                                del option_s_myhave_temp['code'][ot]
                                                                del option_s_myhave_temp['myhave_cnt'][ot]
                                                                del option_s_myhave_temp['sell_or_buy'][ot]
                                                                self.printt('#  옵션 임시재고에서도 빼주고 만일 myhave_cnt 0이라면 리스트에서 삭제')
                                                                break  # 리스트 요소를 삭제하였으므로 for문 중지
                # print(myhave_option_s_delta)
                # print(option_s_myhave_temp)

        # print(item_list_cnt)
        # print(option_s_myhave_temp)

        # -----
        # 옵션의 최종 재고 목표
        # 검색종목과 임시재고 합치고
        # 종목 중복 제거 건수 합치기
        if len(item_list_cnt['code_no']) > 0:
            # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
            for i in range(len(item_list_cnt['code_no'])):
                if item_list_cnt['code_no'][i] in item_list_cnt_tarket['code_no']:
                    for j in range(len(item_list_cnt_tarket['code_no'])):
                        if item_list_cnt['code_no'][i] == item_list_cnt_tarket['code_no'][j]:
                            item_list_cnt_tarket['cnt'][j] += item_list_cnt['cnt'][i]
                else:
                    item_list_cnt_tarket['code_no'].append(item_list_cnt['code_no'][i])
                    item_list_cnt_tarket['cnt'].append(item_list_cnt['cnt'][i])
                    item_list_cnt_tarket['sell_buy_type'].append(item_list_cnt['sell_buy_type'][i])
            # print(item_list_cnt_tarket)
            # 검색종목과 임시재고 합치기
            for i in range(len(option_s_myhave_temp['code'])):
                if option_s_myhave_temp['code'][i] in item_list_cnt_tarket['code_no']:
                    for j in range(len(item_list_cnt_tarket['code_no'])):
                        if option_s_myhave_temp['code'][i] == item_list_cnt_tarket['code_no'][j]:
                            if option_s_myhave_temp['sell_or_buy'][i] == item_list_cnt_tarket['sell_buy_type'][j]:
                                item_list_cnt_tarket['cnt'][j] += (option_s_myhave_temp['myhave_cnt'][i])
                            elif option_s_myhave_temp['sell_or_buy'][i] != item_list_cnt_tarket['sell_buy_type'][j]:
                                item_list_cnt_tarket['code_no'].append(option_s_myhave_temp['code'][i])
                                item_list_cnt_tarket['cnt'].append(option_s_myhave_temp['myhave_cnt'][i])
                                item_list_cnt_tarket['sell_buy_type'].append(option_s_myhave_temp['sell_or_buy'][i])
                else:
                    item_list_cnt_tarket['code_no'].append(option_s_myhave_temp['code'][i])
                    item_list_cnt_tarket['cnt'].append(option_s_myhave_temp['myhave_cnt'][i])
                    item_list_cnt_tarket['sell_buy_type'].append(option_s_myhave_temp['sell_or_buy'][i])
            # print(item_list_cnt_tarket)
        # 검색종목과 임시재고 합치고
        elif len(option_s_myhave_temp['code']) > 0:
            # 검색종목과 임시재고 합치기
            for i in range(len(option_s_myhave_temp['code'])):
                if option_s_myhave_temp['code'][i] in item_list_cnt['code_no']:
                    for j in range(len(item_list_cnt['code_no'])):
                        if option_s_myhave_temp['code'][i] == item_list_cnt['code_no'][j]:
                            if option_s_myhave_temp['sell_or_buy'][i] == item_list_cnt['sell_buy_type'][j]:
                                item_list_cnt_tarket['cnt'][j] += (option_s_myhave_temp['myhave_cnt'][i])
                            elif option_s_myhave_temp['sell_or_buy'][i] != item_list_cnt['sell_buy_type'][j]:
                                item_list_cnt_tarket['code_no'].append(option_s_myhave_temp['code'][i])
                                item_list_cnt_tarket['cnt'].append(option_s_myhave_temp['myhave_cnt'][i])
                                item_list_cnt_tarket['sell_buy_type'].append(option_s_myhave_temp['sell_or_buy'][i])

                else:
                    item_list_cnt_tarket['code_no'].append(option_s_myhave_temp['code'][i])
                    item_list_cnt_tarket['cnt'].append(option_s_myhave_temp['myhave_cnt'][i])
                    item_list_cnt_tarket['sell_buy_type'].append(option_s_myhave_temp['sell_or_buy'][i])
            # print(item_list_cnt_tarket)
        # -----

        # -----
        # 재고 항목과 검색항목 비교하여 매도 매수 정하기
        # 보유목록이 검색목록에 있거나 없거나
        # 보유 목록 돌리고
        for p in range(len(self.option_myhave['code'])):
            if self.option_myhave['code'][p] in item_list_cnt_tarket['code_no']:
                # 아래에서 처리
                pass
            # 보유 재고중에 매수는 없다고 가정 :: 매도를 매수처리
            elif self.option_myhave['sell_or_buy'][p] == 1:
                if self.option_myhave['code'][p][:3] != '101':
                    item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    item_list_cnt_type['sell_buy_type'].append(2)
        # 검색 목록 모두 돌리고 검색결과 값 넣어주고
        for it in range(len(item_list_cnt_tarket['code_no'])):
            # 검색목록이 보유목록에 있거나 없거나
            if item_list_cnt_tarket['code_no'][it] in self.option_myhave['code']:
                # 보유 목록 돌리고
                for p in range(len(self.option_myhave['code'])):
                    # 종목코드 비교
                    if item_list_cnt_tarket['code_no'][it] == self.option_myhave['code'][p]:
                        # 매도 매수 타입 비교
                        # 보유 재고중에 매수는 없다고 가정하고[왜냐하면 매수가 있으면 매도종목의 종류가 1개 이상이 되므로 - 매도 종목은 오로지 1개로만]
                        if item_list_cnt_tarket['sell_buy_type'][it] == 1:
                            # 재고 건수 비교하여 동일하면 진입 필요없음
                            if item_list_cnt_tarket['cnt'][it] == self.option_myhave['myhave_cnt'][p]:
                                pass
                            # 보유 재고가 크면 매수 처리해야함
                            elif item_list_cnt_tarket['cnt'][it] < self.option_myhave['myhave_cnt'][p]:
                                diff_cnt = self.option_myhave['myhave_cnt'][p] - item_list_cnt_tarket['cnt'][it]
                                item_list_cnt_type['code_no'].append(item_list_cnt_tarket['code_no'][it])
                                item_list_cnt_type['cnt'].append(diff_cnt)
                                item_list_cnt_type['sell_buy_type'].append(2)
                            # 검색 목록이 크면 건수 만큼 매도
                            elif item_list_cnt_tarket['cnt'][it] > self.option_myhave['myhave_cnt'][p]:
                                diff_cnt = item_list_cnt_tarket['cnt'][it] - self.option_myhave['myhave_cnt'][p]
                                item_list_cnt_type['code_no'].append(item_list_cnt_tarket['code_no'][it])
                                item_list_cnt_type['cnt'].append(diff_cnt)
                                item_list_cnt_type['sell_buy_type'].append(item_list_cnt_tarket['sell_buy_type'][it])
                        # 매도 매수 타입 비교
                        elif item_list_cnt_tarket['sell_buy_type'][it] == 2:
                            # 보유 재고중에 매수는 없다고 가정
                            if self.option_myhave['sell_or_buy'][p] == 1:
                                item_list_cnt_type['code_no'].append(item_list_cnt_tarket['code_no'][it])
                                item_list_cnt_type['cnt'].append(item_list_cnt_tarket['cnt'][it])
                                item_list_cnt_type['sell_buy_type'].append(item_list_cnt_tarket['sell_buy_type'][it])
            # 검색목록이 보유목록에 없으면 모두 넣어주고
            else:
                item_list_cnt_type['code_no'].append(item_list_cnt_tarket['code_no'][it])
                item_list_cnt_type['cnt'].append(item_list_cnt_tarket['cnt'][it])
                item_list_cnt_type['sell_buy_type'].append(item_list_cnt_tarket['sell_buy_type'][it])
        # -----

        # print(item_list_cnt)
        return item_list_cnt_type

    # 선물매도/매수 :: 풋진입/콜진입 :: 풋청산/콜청산
    def future_s_market_sell_buy(self, item_list_cnt_type):
        cross_winner = []
        volume_listed_var = []
        item_list = []
        sOrgOrdNo = []
        for i in range(len(item_list_cnt_type['code_no'])):
            # 풋옵션
            if item_list_cnt_type['code_no'][i][:3] == '301':
                if item_list_cnt_type['sell_buy_type'][i] == 1:  # 매도
                    # 시간표시
                    current_time = time.ctime()
                    self.printt('-----')
                    self.printt(current_time)
                    self.printt('item_list_cnt_type')
                    self.printt(item_list_cnt_type)
                    self.printt('Send Option Order')
                    self.printt('# 풋매도')
                    cross_winner_cell = 9004
                    self.printt(cross_winner_cell)
                    sOrgOrdNo_cell = ''
                    cross_winner.append(cross_winner_cell)
                    volume_listed_var.append(item_list_cnt_type['cnt'][i])
                    item_list.append(item_list_cnt_type['code_no'][i])
                    sOrgOrdNo.append(sOrgOrdNo_cell)
                elif item_list_cnt_type['sell_buy_type'][i] == 2:  # 매수
                    # 시간표시
                    current_time = time.ctime()
                    self.printt('-----')
                    self.printt(current_time)
                    self.printt('item_list_cnt_type')
                    self.printt(item_list_cnt_type)
                    self.printt('Send Option Order')
                    self.printt('# 풋매수')
                    cross_winner_cell = 3004
                    self.printt(cross_winner_cell)
                    sOrgOrdNo_cell = ''
                    cross_winner.append(cross_winner_cell)
                    volume_listed_var.append(item_list_cnt_type['cnt'][i])
                    item_list.append(item_list_cnt_type['code_no'][i])
                    sOrgOrdNo.append(sOrgOrdNo_cell)
            # 콜옵션
            elif item_list_cnt_type['code_no'][i][:3] == '201':
                if item_list_cnt_type['sell_buy_type'][i] == 1:  # 매도
                    # 시간표시
                    current_time = time.ctime()
                    self.printt('-----')
                    self.printt(current_time)
                    self.printt('item_list_cnt_type')
                    self.printt(item_list_cnt_type)
                    self.printt('Send Option Order')
                    self.printt('# 콜매도')
                    cross_winner_cell = 8004
                    self.printt(cross_winner_cell)
                    sOrgOrdNo_cell = ''
                    cross_winner.append(cross_winner_cell)
                    volume_listed_var.append(item_list_cnt_type['cnt'][i])
                    item_list.append(item_list_cnt_type['code_no'][i])
                    sOrgOrdNo.append(sOrgOrdNo_cell)
                elif item_list_cnt_type['sell_buy_type'][i] == 2:  # 매수
                    # 시간표시
                    current_time = time.ctime()
                    self.printt('-----')
                    self.printt(current_time)
                    self.printt('item_list_cnt_type')
                    self.printt(item_list_cnt_type)
                    self.printt('Send Option Order')
                    self.printt('# 콜매수')
                    cross_winner_cell = 2004
                    self.printt(cross_winner_cell)
                    sOrgOrdNo_cell = ''
                    cross_winner.append(cross_winner_cell)
                    volume_listed_var.append(item_list_cnt_type['cnt'][i])
                    item_list.append(item_list_cnt_type['code_no'][i])
                    sOrgOrdNo.append(sOrgOrdNo_cell)
            # 선물
            elif item_list_cnt_type['code_no'][i][:3] == '101':
                if item_list_cnt_type['sell_buy_type'][i] == 1:  # 매도
                    # 시간표시
                    current_time = time.ctime()
                    self.printt('-----')
                    self.printt(current_time)
                    self.printt('item_list_cnt_type')
                    self.printt(item_list_cnt_type)
                    self.printt('Send futrue_s Order')
                    self.printt('# 선물매도')
                    cross_winner_cell = 6004
                    self.printt(cross_winner_cell)
                    sOrgOrdNo_cell = ''
                    cross_winner.append(cross_winner_cell)
                    volume_listed_var.append(item_list_cnt_type['cnt'][i])
                    item_list.append(item_list_cnt_type['code_no'][i])
                    sOrgOrdNo.append(sOrgOrdNo_cell)
                elif item_list_cnt_type['sell_buy_type'][i] == 2:  # 매수
                    # 시간표시
                    current_time = time.ctime()
                    self.printt('-----')
                    self.printt(current_time)
                    self.printt('item_list_cnt_type')
                    self.printt(item_list_cnt_type)
                    self.printt('Send futrue_s Order')
                    self.printt('# 선물매수')
                    cross_winner_cell = 4004
                    self.printt(cross_winner_cell)
                    sOrgOrdNo_cell = ''
                    cross_winner.append(cross_winner_cell)
                    volume_listed_var.append(item_list_cnt_type['cnt'][i])
                    item_list.append(item_list_cnt_type['code_no'][i])
                    sOrgOrdNo.append(sOrgOrdNo_cell)
        self.printt('volume_listed_var / item_list')
        self.printt(cross_winner)
        self.printt(volume_listed_var)
        self.printt(item_list)
        self.printt(sOrgOrdNo)

        # 자동주문 주문실행
        self.order_ready(cross_winner, volume_listed_var, item_list, sOrgOrdNo)


    # put_item_list_text_store
    def put_item_list_text_store(self, put_item_list_cnt):
        # item_list.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # put_item_list_cnt
        f = open(item_list_files_path + self.Global_Option_Item_Code_var + "_" + "put_item_list_cnt.txt", 'wt', encoding='UTF8')
        for i in range(len(put_item_list_cnt['code_no'])):
            code = put_item_list_cnt['code_no'][i]
            cnt = str(put_item_list_cnt['cnt'][i])
            store_data = code + ';' + cnt
            f.write(store_data + '\n')
        f.close()

    # call_item_list_text_store
    def call_item_list_text_store(self, call_item_list_cnt):
        # item_list.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # call_item_list_cnt['code_no']
        f = open(item_list_files_path + self.Global_Option_Item_Code_var + "_" + "call_item_list_cnt.txt", 'wt', encoding='UTF8')
        for i in range(len(call_item_list_cnt['code_no'])):
            code = call_item_list_cnt['code_no'][i]
            cnt = str(call_item_list_cnt['cnt'][i])
            store_data = code + ';' + cnt
            f.write(store_data + '\n')
        f.close()

    # option_s_sell_buy_point 텍스트 저장
    def option_s_sell_buy_point_store_fn(self, option_s_sell_buy_point):
        # option_s_sell_buy_point.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # option_s_sell_buy_point  # int
        f = open(item_list_files_path + "option_s_sell_buy_point_text.txt", 'at', encoding='UTF8')
        store_data = str(option_s_sell_buy_point)
        f.write(store_data + '\n')
        f.close()
    def option_s_sell_buy_point_text_pickup(self):
        # 변수선언
        item_list = []
        # option_s_sell_buy_point.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # option_s_sell_buy_point  # int
        f = open(item_list_files_path + "option_s_sell_buy_point_text.txt", 'rt', encoding='UTF8')
        option_s_sell_buy_point_readlines = f.readlines()
        # print(option_s_sell_buy_point_readlines)
        f.close()

        # 리스트 저장
        for i in range(len(option_s_sell_buy_point_readlines)):
            last_order_item_new = option_s_sell_buy_point_readlines[i].strip()   # 엔터제거
            item_list.append(float(last_order_item_new))
        # print(item_list)
        return item_list

    # today_put_order_list_text_store
    def today_put_order_list_text_store(self, put_item_list_cnt):
        # item_list.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # put_item_list_cnt['code_no']
        f = open(item_list_files_path + "today_put_order_lists.txt", 'at',
                 encoding='UTF8')
        store_data = ''
        for i in range(len(put_item_list_cnt['code_no'])):
            code = put_item_list_cnt['code_no'][i]
            cnt = str(put_item_list_cnt['cnt'][i])
            store_data = store_data + code + '::' + cnt + '::'
        f.write(store_data + '\n')
        f.close()
    def today_put_order_list_text_pickup(self):
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': []}

        # item_list.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # call_item_list_cnt['code_no']
        f = open(item_list_files_path + "today_put_order_lists.txt", 'rt',
                 encoding='UTF8')
        order_list_readlines = f.readlines()
        # print(order_list_readlines)
        f.close()

        # 맨 마지막 라인 챙기기
        if len(order_list_readlines) != 0:
            last_order_item = order_list_readlines[-1]
            del order_list_readlines[-1]
            # print(last_order_item)
            last_order_item_new = last_order_item.strip()
            # print(last_order_item_new)
            item = last_order_item_new.split('::')
            print(item)
            for i in range(0, (len(item) - 1), 2):
                item_list_cnt['code_no'].append(item[i])
                item_list_cnt['cnt'].append(int(item[i + 1]))
        # print(item_list_cnt)
        # print(order_list_readlines)

        # 텍스트 파일에 다시 저장
        f = open(item_list_files_path + "today_put_order_lists.txt", 'wt',
                 encoding='UTF8')
        for order_list in order_list_readlines:
            f.write(order_list)
        f.close()

        return item_list_cnt

    # today_call_order_list_text_store
    def today_call_order_list_text_store(self, call_item_list_cnt):
        # item_list.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # call_item_list_cnt['code_no']
        f = open(item_list_files_path + "today_call_order_lists.txt", 'at',
                 encoding='UTF8')
        store_data = ''
        for i in range(len(call_item_list_cnt['code_no'])):
            code = call_item_list_cnt['code_no'][i]
            cnt = str(call_item_list_cnt['cnt'][i])
            store_data = store_data + code + '::' + cnt + '::'
        f.write(store_data + '\n')
        f.close()
    def today_call_order_list_text_pickup(self):
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': []}

        # item_list.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # call_item_list_cnt['code_no']
        f = open(item_list_files_path + "today_call_order_lists.txt", 'rt',
                 encoding='UTF8')
        order_list_readlines = f.readlines()
        # print(order_list_readlines)
        f.close()

        # 맨 마지막 라인 챙기기
        if len(order_list_readlines) != 0:
            last_order_item = order_list_readlines[-1]
            del order_list_readlines[-1]
            # print(last_order_item)
            last_order_item_new = last_order_item.strip()
            # print(last_order_item_new)
            item = last_order_item_new.split('::')
            print(item)
            for i in range(0, (len(item) - 1), 2):
                item_list_cnt['code_no'].append(item[i])
                item_list_cnt['cnt'].append(int(item[i + 1]))
        # print(item_list_cnt)
        # print(order_list_readlines)

        # 텍스트 파일에 다시 저장
        f = open(item_list_files_path + "today_call_order_lists.txt", 'wt',
                 encoding='UTF8')
        for order_list in order_list_readlines:
            f.write(order_list)
        f.close()

        return item_list_cnt

    # future_s_basket_cnt_text_store
    def future_s_basket_cnt_text_store(self, basket_cnt):
        # txt_store 폴더
        txt_file_path = os.getcwd() + '/' + Folder_Name_TXT_Store
        is_txt_file = os.path.isdir(txt_file_path)
        if is_txt_file == False:
            os.makedirs(txt_file_path)

        # basket_cnt.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # basket_cnt  # int
        f = open(item_list_files_path + "future_s_basket_cnt_text.txt", 'wt', encoding='UTF8')
        store_data = str(basket_cnt)
        f.write(store_data)
        f.close()

    # future_s_basket_cnt_text_read
    def future_s_basket_cnt_text_read(self):
        # choice_filename_with
        choice_filename_with = 'future_s_basket_cnt_text'
        # txt_store 폴더
        txt_file_path = os.getcwd() + '/' + Folder_Name_TXT_Store
        is_txt_file = os.path.isdir(txt_file_path)
        # print(txt_file_path)
        # C:\Users\ceo\Desktop\fu2060/txt_store
        if is_txt_file == False:
            os.makedirs(txt_file_path)

        # basket_cnt.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        dir_list_files = os.listdir(item_list_files_path)
        # print(dir_list_files)
        # ['2024', 'future_s_basket_cnt_text.txt']

        # choice_files_list 리스트 생성
        choice_files_list = []
        for f in dir_list_files:
            if f.startswith(choice_filename_with):
                choice_files_list.append(f)
        # print(choice_files_list)
        # ['future_s_basket_cnt_text.txt']
        # choice_files_list 파일이 없으면 0
        if len(choice_files_list) == 0:
            return 1

        # 당일 파일에서 basket_cnt
        for file_name in choice_files_list:
            file_path_name = txt_file_path + '/' + file_name
            f = open(file_path_name, 'rt', encoding='UTF8')
            basket_cnt_readlines = f.readlines()
            f.close()
        # print(basket_cnt_readlines)
        basket_cnt = int(basket_cnt_readlines[-1])
        return basket_cnt




















































































































    # 자동으로 주문하는 기능은 MyWindow 클래스의 trade_stocks 메서드에 구현
    def trade_stocks(self):
        hoga_lookup = {'지정가': "00", '시장가': "03"}

        f = open("buy_list.txt", 'rt')
        buy_list = f.readlines()
        f.close()

        f = open("sell_list.txt", 'rt')
        sell_list = f.readlines()
        f.close()

        # 주문할 때 필요한 계좌 정보를 QComboBox 위젯으로부터
        account = self.comboBox_acc.currentText()

        # buy_list로부터 데이터를 하나씩 얻어온 후 문자열을 분리해서 주문에 필요한 정보(거래구분, 종목코드, 수량, 가격)를 준비
        # buy list
        for row_data in buy_list:
            split_row_data = row_data.split(';')
            hoga = split_row_data[2]
            code = split_row_data[1]
            num = split_row_data[3]
            price = split_row_data[4]

            if split_row_data[-1].rstrip() == '매수전':
                self.kiwoom.send_order("send_order_req", "0101", account, 1, code, num, price, hoga_lookup[hoga], "")

        # sell list
        for row_data in sell_list:
            split_row_data = row_data.split(';')
            hoga = split_row_data[2]
            code = split_row_data[1]
            num = split_row_data[3]
            price = split_row_data[4]

            if split_row_data[-1].rstrip() == '매도전':
                self.kiwoom.send_order("send_order_req", "0101", account, 2, code, num, price, hoga_lookup[hoga], "")

        # 매매 주문이 완료되면 buy_list.txt나 sell_list.txt에 저장된 주문 여부를 업데이트
        # buy list
        for i, row_data in enumerate(buy_list):
            buy_list[i] = buy_list[i].replace("매수전", "주문완료")

        # file update
        f = open("buy_list.txt", 'wt')
        for row_data in buy_list:
            f.write(row_data)
        f.close()

        # sell list
        for i, row_data in enumerate(sell_list):
            sell_list[i] = sell_list[i].replace("매도전", "주문완료")

        # file update
        f = open("sell_list.txt", 'wt')
        for row_data in sell_list:
            f.write(row_data)
        f.close()

    # buy_list.txt와 sell_list.txt 파일을 열고 파일로부터 데이터를 읽는 코드를 구현
    def load_buy_sell_list(self):
        f = open("buy_list.txt", 'rt',  encoding='UTF8')
        buy_list = f.readlines()
        f.close()

        f = open("sell_list.txt", 'rt',  encoding='UTF8')
        sell_list = f.readlines()
        f.close()

        # 데이터의 총 개수를 확인합니다. 매수/매도 종목 각각에 대한 데이터 개수를 확인한 후 이 두 값을 더한 값을 QTableWidet 객체의 setRowCount 메서드로 설정
        row_count = len(buy_list) + len(sell_list)
        self.tableWidget_4.setRowCount(row_count)

        # buy list
        for j in range(len(buy_list)):
            row_data = buy_list[j]
            split_row_data = row_data.split(';')
            split_row_data[1] = self.kiwoom.get_master_code_name(split_row_data[1].rsplit())

            for i in range(len(split_row_data)):
                item = QTableWidgetItem(split_row_data[i].rstrip())
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.tableWidget_4.setItem(j, i, item)

        # sell list
        for j in range(len(sell_list)):
            row_data = sell_list[j]
            split_row_data = row_data.split(';')
            split_row_data[1] = self.kiwoom.get_master_code_name(split_row_data[1].rstrip())

            for i in range(len(split_row_data)):
                item = QTableWidgetItem(split_row_data[i].rstrip())
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.tableWidget_4.setItem(len(buy_list) + j, i, item)

        # QTableWidget에서 행의 크기를 조절하기 위해 resizeRowsToContents 메서드를 호출
        self.tableWidget_4.resizeRowsToContents()

    # opw00018 TR을 위한 입력 데이터 설정(SetInputValue)과 TR을 요청(CommRqDat)하는 코드를 구현
    def check_balance(self):
        # Kiwoom클래스에서 인스턴스 변수 선언
        self.kiwoom.reset_output()
        account_number = self.kiwoom.get_login_info("ACCNO")
        account_number = account_number.split(';')[0]

        self.kiwoom.set_input_value("계좌번호", account_number)
        self.kiwoom.comm_rq_data("opw00018_req", "opw00018", 0, "2000")

        while self.kiwoom.remained_data:
            time.sleep(0.2)
            self.kiwoom.set_input_value("계좌번호", account_number)
            self.kiwoom.comm_rq_data("opw00018_req", "opw00018", 2, "2000")

        # opw00001
        # 예수금 데이터를 얻기 위해 opw00001 TR을 요청하는 코드를 구현
        self.kiwoom.set_input_value("계좌번호", account_number)
        self.kiwoom.comm_rq_data("opw00001_req", "opw00001", 0, "2000")

        # balance
        # self.kiwoom.d2_deposit에 저장된 예수금 데이터를 QTableWidgetItem 객체로 만듭
        item = QTableWidgetItem(self.kiwoom.d2_deposit)
        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.tableWidget.setItem(0, 0, item)

        for i in range(1, 6):
            item = QTableWidgetItem(self.kiwoom.output['single'][i - 1])
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            self.tableWidget.setItem(0, i, item)

        self.tableWidget.resizeRowsToContents()

        # Item list
        # 보유 종목별 평가 잔고 데이터를 QTableWidget에 추가
        item_count = len(self.kiwoom.output['multi'])
        self.tableWidget_2.setRowCount(item_count)

        for j in range(item_count):
            row = self.kiwoom.output['multi'][j]
            for i in range(len(row)):
                item = QTableWidgetItem(row[i])
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                self.tableWidget_2.setItem(j, i, item)

        self.tableWidget_2.resizeRowsToContents()

    # # MyWindow 클래스에 code_changed 메서드를 다음과 같이 구현
    # def code_changed(self):
    #     code = self.lineEdit.text()
    #     name = self.kiwoom.get_master_code_name(code)
    #     self.lineEdit_2.setText(name)

    def timer_stopper(self, text_time):
        # 임시테스트 타이머 죽이기 / 실시간 데이터 죽이기
        self.timer.stop()
        self.kiwoom.SetRealRemove("ALL", "ALL")










    # 저장 함수
    def data_store_ready(self, store_time_var, output_call_option_data, output_put_option_data):
        # db명 설정
        current_monthmall = self.current_monthmall_var
        data_store(store_time_var, Folder_Name_DB_Store, self.Global_Option_Item_Code_var, Up_CenterOption_Down, current_monthmall, self.center_index, output_call_option_data, output_put_option_data)

    # 가져오기 함수
    def data_pickup_ready(self):
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(Folder_Name_DB_Store)
        if is_store_folder == False:
            return

        dir_list_year = os.listdir(Folder_Name_DB_Store)
        # print(dir_list_year)
        # db 파일 제거
        dir_list_year_only_dir = []
        for dir in dir_list_year:
            if dir.endswith('.db'):
                continue
            dir_list_year_only_dir.append(dir)

        # 콤보박스 넣어주기(년)
        self.comboBox_year.clear()
        self.comboBox_year.addItems(dir_list_year_only_dir)

        # 카운터
        combobox_year_cnt = self.comboBox_year.count()
        # print(combobox_year_cnt)
        # 마지막 인텍스 선택
        if combobox_year_cnt != 0:
            self.comboBox_year.setCurrentIndex(combobox_year_cnt - 1)

        # # currentIndexChanged 이벤트 핸들러
        # self.comboBox_year.activated.connect(self.select_monthmall)

        self.select_monthmall()

    def select_monthmall(self):
        # 폴더
        current_year = self.comboBox_year.currentText()
        # print(current_year)
        dir_list_monthmall = os.listdir(Folder_Name_DB_Store + '/' + current_year)
        # print(dir_list_monthmall)

        # 콤보박스 넣어주기(월물)
        self.comboBox_monthmall.clear()
        # 앞뒤 텍스트 버리기
        only_monthmall = []
        for i in dir_list_monthmall:
            if (i.startswith(Global_Option_Item_Code)) and (i.endswith('.db')):
                only_monthmall.append(i[5:-3])
        # print(only_monthmall)
        # 여러 기초자산으로 운용계획이므로 혹시 선택한 db 없을때는 리턴
        if len(only_monthmall) == 0:
            return
        self.comboBox_monthmall.addItems(only_monthmall)

        # 카운터
        combobox_monthmll_cnt = self.comboBox_monthmall.count()
        # print(combobox_monthmll_cnt)
        # 마지막 인텍스 선택
        self.comboBox_monthmall.setCurrentIndex(combobox_monthmll_cnt - 1)

        # # currentIndexChanged 이벤트 핸들러
        # self.comboBox_monthmall.activated.connect(self.select_date)

        self.select_date()

    def select_date(self):
        # 폴더
        plus_current_monthmall = self.comboBox_monthmall.currentText()
        # print(current_monthmall)
        # folder_name_year = datetime.datetime.today().strftime("%Y")
        folder_name_year = self.comboBox_year.currentText()  # 20200918 년폴더 수정
        # db명 설정
        db_name = Folder_Name_DB_Store + '/' + folder_name_year + '/' + Global_Option_Item_Code + '_' + plus_current_monthmall + '.db'
        # print(db_name)

        # 테이블명 가져오기
        con = sqlite3.connect(db_name)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name = cursor.fetchall()
        # db닫기
        con.commit()
        con.close()
        # print(total_table_name)
        table_name_list = []
        for i in total_table_name:
            table_name_list.append(i[0])
        # print(table_name_list)

        # 콤보박스 넣어주기()
        self.comboBox_date.clear()
        self.comboBox_date.addItems(table_name_list)
        # 마지막 인텍스 선택
        combobox_date_cnt = self.comboBox_date.count()
        self.comboBox_date.setCurrentIndex(combobox_date_cnt - 1)

        # # currentIndexChanged 이벤트 핸들러
        # self.comboBox_date.activated.connect(self.select_time)

        self.select_time()

    def select_time(self):
        # 폴더
        plus_current_monthmall = self.comboBox_monthmall.currentText()
        # print(current_monthmall)
        # folder_name_year = datetime.datetime.today().strftime("%Y")
        folder_name_year = self.comboBox_year.currentText()  # 20200918 년폴더 수정
        # db명 설정
        db_name = Folder_Name_DB_Store + '/' + folder_name_year + '/' + Global_Option_Item_Code + '_' + plus_current_monthmall + '.db'
        # 테이블명 설정
        table_name = self.comboBox_date.currentText()
        # print(table_name)

        # 데이타 가져오기 함수 호출
        data_pickup_ret = data_pickup(db_name, table_name)

        # 중심가[9] 기준으로 중복제거
        new_data_pickup_ret = data_pickup_ret[data_pickup_ret['option_price'] == (data_pickup_ret['option_price'][9])]
        # print(new_data_pickup_ret['time'])
        # 리스트 만들고
        time_str_labels = []
        for time_data in (new_data_pickup_ret['time']):
            time_str_labels.append(time_data)
        # print(time_str_labels)

        # 다항회귀 수동보기에서 첫번째 시간 제거를 위한
        del time_str_labels[0]
        # 콤보박스 넣어주기(시분)
        self.comboBox_time.clear()
        self.comboBox_time.addItems(time_str_labels)
        # 마지막 인텍스 선택
        combobox_time_cnt = self.comboBox_time.count()
        self.comboBox_time.setCurrentIndex(combobox_time_cnt - 1)

        # # currentIndexChanged 이벤트 핸들러
        # self.comboBox_time.activated.connect(self.listed_slot)

        # DB 저당된 옵션데이타 가져다가 리스트 뿌리기
        self.listed_slot()

    # DB 저당된 옵션데이타 가져다가 리스트 뿌리기
    def listed_slot(self):
        # 폴더
        plus_current_monthmall = self.comboBox_monthmall.currentText()
        # print(current_monthmall)
        # folder_name_year = datetime.datetime.today().strftime("%Y")
        folder_name_year = self.comboBox_year.currentText()  # 20200918 년폴더 수정
        # db명 설정
        db_name = Folder_Name_DB_Store + '/' + folder_name_year + '/' + Global_Option_Item_Code + '_' + plus_current_monthmall + '.db'
        # 테이블명 설정
        table_name = self.comboBox_date.currentText()
        # print(table_name)
        # 데이타 가져오기 함수 호출
        data_pickup_ret = data_pickup(db_name, table_name)

        # 선택시간
        select_time = self.comboBox_time.currentText()
        if select_time != '':
            # 선택시간 기준으로 데이타 수집
            # print(select_time)
            select_time_df_read = data_pickup_ret[data_pickup_ret['time'] <= select_time]
            # print(select_time_df_read)
            # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
            min_index = select_time_df_read.index.min()
            max_index = select_time_df_read.index.max()
            # print(max_index)
            # print(select_time_df_read)
        else:
            # 선택시간 기준으로 데이타 수집
            # print(select_time)
            select_time_df_read = data_pickup_ret
            # print(select_time_df_read)
            # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
            min_index = data_pickup_ret.index.min()
            max_index = select_time_df_read.index.max()
            # print(max_index)
            # print(data_pickup_ret)

        # 테이블 위젯에 리스트 뿌리기
        listed_cnt = (Up_CenterOption_Down * 2) + 1
        self.tableWidget_optionprice.setRowCount(listed_cnt)
        for j in range(listed_cnt):
            str_call_vol_cnt = str(select_time_df_read['call_vol_cnt'][max_index - (listed_cnt - 1) + j])
            str_call_run_price = str(select_time_df_read['call_run_price'][max_index - (listed_cnt - 1) + j])
            str_put_run_price = str(select_time_df_read['put_run_price'][max_index - (listed_cnt - 1) + j])
            str_put_vol_cnt = str(select_time_df_read['put_vol_cnt'][max_index - (listed_cnt - 1) + j])

            self.tableWidget_optionprice.setItem(j, 0, QTableWidgetItem(str_call_vol_cnt))
            self.tableWidget_optionprice.setItem(j, 1, QTableWidgetItem(str_call_run_price))
            self.tableWidget_optionprice.setItem(j, 2, QTableWidgetItem(select_time_df_read['option_price'][max_index - (listed_cnt - 1) + j]))
            self.tableWidget_optionprice.setItem(j, 3, QTableWidgetItem(str_put_run_price))
            self.tableWidget_optionprice.setItem(j, 4, QTableWidgetItem(str_put_vol_cnt))

        # [실시간 조회] 체크박스가 켜져있을때만
        if self.checkbox_realtime.isChecked():
            self.draw_chart_future_s_real_poly(table_name, select_time_df_read, min_index, Chart_Ylim,
                                               Up_CenterOption_Down)
        else:
            # 차트 그리기
            self.draw_chart(table_name, select_time_df_read, min_index, Chart_Ylim, Up_CenterOption_Down)

    # 가저오기 함수(1초)
    def data_pickup_1sec(self):
        # 월물 설정
        current_monthmall = self.current_monthmall_var
        # year 폴더
        folder_name_year = current_monthmall[:4]
        # db명 설정
        db_name = os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year + '/' + self.Global_Option_Item_Code_var + '_' + current_monthmall + '.db'
        # db명 존재여부 체크
        is_file = os.path.exists(db_name)
        if is_file == False :
            return

        # 테이블명 설정
        table_name_today = datetime.datetime.today().strftime("%Y%m%d")

        # 데이타 가져오기 함수 호출
        data_pickup_ret = data_pickup(db_name, table_name_today)

        # 선택시간 기준으로 데이타 수집
        # print(select_time)
        select_time_df_read = data_pickup_ret
        # print(select_time_df_read)
        # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
        min_index = data_pickup_ret.index.min()
        max_index = select_time_df_read.index.max()
        # print(min_index)
        # print(data_pickup_ret)

        # 테이블 위젯에 리스트 뿌리기
        listed_cnt = (Up_CenterOption_Down * 2) + 1
        self.tableWidget_optionprice.setRowCount(listed_cnt)
        for j in range(listed_cnt):
            str_call_vol_cnt = str(select_time_df_read['call_vol_cnt'][max_index - (listed_cnt - 1) + j])
            str_call_run_price = str(select_time_df_read['call_run_price'][max_index - (listed_cnt - 1) + j])
            str_put_run_price = str(select_time_df_read['put_run_price'][max_index - (listed_cnt - 1) + j])
            str_put_vol_cnt = str(select_time_df_read['put_vol_cnt'][max_index - (listed_cnt - 1) + j])

            self.tableWidget_optionprice.setItem(j, 0, QTableWidgetItem(str_call_vol_cnt))
            self.tableWidget_optionprice.setItem(j, 1, QTableWidgetItem(str_call_run_price))
            self.tableWidget_optionprice.setItem(j, 2, QTableWidgetItem(select_time_df_read['option_price'][max_index - (listed_cnt - 1) + j]))
            self.tableWidget_optionprice.setItem(j, 3, QTableWidgetItem(str_put_run_price))
            self.tableWidget_optionprice.setItem(j, 4, QTableWidgetItem(str_put_vol_cnt))

        future_s_two_time_two_price = self.draw_chart_future_s_real_poly(table_name_today, select_time_df_read, min_index, Chart_Ylim, Up_CenterOption_Down)
        # # print(future_s_two_time_two_price)
        # self.future_s_sell_time_final_price = future_s_two_time_two_price[0]
        # self.future_s_buy_time_final_price = future_s_two_time_two_price[1]
        # self.poly_future_s_gradient = future_s_two_time_two_price[2]

    # 가저오기 함수::월봉(연결선물 차트그리기)
    def data_pickup_future_s_chain_month_select_fill(self):
        # AI trend_line
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # db명 설정
        get_db_name = 'future_s_shlc_data_month' + '.db'
        # 테이블명 가져오기
        con = sqlite3.connect(db_file_path + '/' + get_db_name)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name_of_db = cursor.fetchall()
        # print(total_table_name_of_db)
        # 실제 테이블 구하기
        total_table_name = []
        for table in total_table_name_of_db:
            total_table_name.append(table[0])
        # print(total_table_name)
        for table_name in total_table_name:
            df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
            # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
            # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
            # print(df_read)
            # df_read.info()
            date_str_labels = []
            for date_data in (df_read['stock_date']):
                date_str_labels.append(date_data)
            # 일자 꺼꾸로 뒤집음
            date_str_labels.reverse()
            # 콤보박스 넣어주기(년)
            self.comboBox_future_s_chain_month.clear()
            self.comboBox_future_s_chain_month.addItems(date_str_labels)
            # 카운터
            combobox_future_s_chain_cnt = self.comboBox_future_s_chain_month.count()
            # print(combobox_future_s_chain_cnt)
            # 마지막 인텍스 선택
            if combobox_future_s_chain_cnt != 0:
                self.comboBox_future_s_chain_month.setCurrentIndex(combobox_future_s_chain_cnt - 1)

            self.data_pickup_future_s_chain_month()
        # db닫기
        con.commit()
        con.close()

    # 가저오기 함수::월봉(연결선물 차트그리기)
    def data_pickup_future_s_chain_month(self):
        # 월봉 또는 일봉
        month_or_day = 'm'
        # 봉갯수(월봉 고정 30개)
        stock_price_candle_cnt = 30
        # [당일제외] 체크박스 체크박스가 켜져있으면
        if self.checkbox_today_x.isChecked():
            checkbox_today_x = True
        else:
            checkbox_today_x = False
        # AI trend_line
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # db명 설정
        get_db_name = 'future_s_shlc_data_month' + '.db'
        # 테이블명 가져오기
        con = sqlite3.connect(db_file_path + '/' + get_db_name)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name_of_db = cursor.fetchall()
        # print(total_table_name_of_db)
        # 실제 테이블 구하기
        total_table_name = []
        for table in total_table_name_of_db:
            total_table_name.append(table[0])
        # print(total_table_name)
        for table_name in total_table_name:
            df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
            # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
            # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
            # print(df_read)
            # df_read.info()
            # 선택년월
            select_combobox_date = self.comboBox_future_s_chain_month.currentText()
            if select_combobox_date != '':
                # 선택시간 기준으로 데이타 수집
                # print(select_combobox_date)
                # [당일제외] 체크박스 체크박스가 켜져있으면
                # 마지막날 데이타는 안가져오고 < / 그렇지 않으면 마지막날 데이타도 가져오고
                if checkbox_today_x == True:
                    df_read_selected = df_read[df_read['stock_date'] < select_combobox_date]
                elif checkbox_today_x == False:
                    df_read_selected = df_read[df_read['stock_date'] <= select_combobox_date]
                # print(df_read_selected)
                # pd 필요건수 만큼 취하고 역순으로 바꾸기
                df_read_use = df_read_selected[(stock_price_candle_cnt - 1)::-1]
                # print(df_read_use)
                # print(len(df_read_use))
                # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
                min_index = df_read_use.index.min()
            else:
                # pd 필요건수 만큼 취하고 역순으로 바꾸기
                df_read_use = df_read[(stock_price_candle_cnt - 1)::-1]
                # print(df_read_use)
                # print(len(df_read_use))
                # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
                min_index = df_read_use.index.min()

            if stock_price_candle_cnt > len(df_read_use):
                return

            # [당일제외] 체크박스 체크박스가 켜져있으면
            # 안가져온 마지막 데이타의 시고저종 취하고
            if checkbox_today_x == True:
                stock_date = df_read['stock_date'][min_index - 1]
                run_price = df_read['stock_end'][min_index - 1]
                start_price = df_read['stock_start'][min_index - 1]
                high_price = df_read['stock_high'][min_index - 1]
                low_price = df_read['stock_low'][min_index - 1]
            # 그렇지 않으면 가져온 마지막 데이타 시고저종 취하고
            elif checkbox_today_x == False:
                stock_date = df_read['stock_date'][min_index]
                run_price = df_read['stock_end'][min_index]
                start_price = df_read['stock_start'][min_index]
                high_price = df_read['stock_high'][min_index]
                low_price = df_read['stock_low'][min_index]
            # print(run_price)

            # 차트 그리기
            self.draw_chart_gui_right(month_or_day, stock_date, df_read_use, min_index, table_name, stock_price_candle_cnt, run_price,
                                      start_price, high_price, low_price, checkbox_today_x)
        # db닫기
        con.commit()
        con.close()

    # 가저오기 함수::일봉(연결선물 & 즐겨찾기 종목 코드)
    def data_pickup_code_s_day_select_fill(self):
        # 필요 테이블 구하기
        total_table_name = []
        # AI trend_line
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # db명 설정
        get_db_name_s = ['future_s_shlc_data_day.db', 'favorites_stock_shlc_data_day.db']
        for get_db_name in get_db_name_s:
            # 테이블명 가져오기
            con = sqlite3.connect(db_file_path + '/' + get_db_name)
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            total_table_name_of_db = cursor.fetchall()
            # print(total_table_name_of_db)

            for table in total_table_name_of_db:
                total_table_name.append(table[0])
            # db닫기
            con.commit()
            con.close()
        # print(total_table_name)

        # 콤보박스 넣어주기(년)
        self.comboBox_code_s_day.clear()
        self.comboBox_code_s_day.addItems(total_table_name)

        # 가저오기 함수::일봉(날자 셀렉트 박스로 가져오기)
        self.data_pickup_date_s_day_select_fill()

    # 가저오기 함수::일봉(날자 셀렉트 박스로 가져오기)
    def data_pickup_date_s_day_select_fill(self):
        # 선택 종목
        select_combobox_code = self.comboBox_code_s_day.currentText()
        # AI trend_line
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # db명 설정
        get_db_name_s = ['future_s_shlc_data_day.db', 'favorites_stock_shlc_data_day.db']
        for get_db_name in get_db_name_s:
            # 테이블명 가져오기
            con = sqlite3.connect(db_file_path + '/' + get_db_name)
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            total_table_name_of_db = cursor.fetchall()
            # print(total_table_name_of_db)
            # 가져온 테이블명을 돌리면서
            for table in total_table_name_of_db:
                # 셀렉트된 종목코드(?)
                if table[0] == select_combobox_code:
                    df_read = pd.read_sql("SELECT * FROM " + "'" + table[0] + "'", con, index_col=None)
                    # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
                    # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
                    # print(df_read)
                    # df_read.info()
                    date_str_labels = []
                    for date_data in (df_read['stock_date']):
                        date_str_labels.append(date_data)
                    # 일자 꺼꾸로 뒤집음
                    date_str_labels.reverse()
                    # 콤보박스 넣어주기(년)
                    self.comboBox_date_s_day.clear()
                    self.comboBox_date_s_day.addItems(date_str_labels)
                    # 카운터
                    combobox_date_s_day_cnt = self.comboBox_date_s_day.count()
                    # print(combobox_date_s_day_cnt)
                    # 마지막 인텍스 선택
                    if combobox_date_s_day_cnt != 0:
                        self.comboBox_date_s_day.setCurrentIndex(combobox_date_s_day_cnt - 1)
            # db닫기
            con.commit()
            con.close()
        # 일봉(차트그리기)
        self.data_pickup_chart_s_day()

    # 가저오기 함수::일봉(차트그리기)
    def data_pickup_chart_s_day(self):
        # 월봉 또는 일봉
        month_or_day = 'd'
        # 일봉 갯수가 선택되지 않았으면 패스
        if self.stock_price_candle_cnt == 0:
            return
        # [당일제외] 체크박스 체크박스가 켜져있으면
        if self.checkbox_today_x.isChecked():
            checkbox_today_x = True
        else:
            checkbox_today_x = False
        # 봉갯수
        stock_price_candle_cnt = self.stock_price_candle_cnt
        # 선택 종목
        select_combobox_code = self.comboBox_code_s_day.currentText()
        # AI trend_line
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # db명 설정
        get_db_name_s = ['future_s_shlc_data_day.db', 'favorites_stock_shlc_data_day.db']
        for get_db_name in get_db_name_s:
            # 테이블명 가져오기
            con = sqlite3.connect(db_file_path + '/' + get_db_name)
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            total_table_name_of_db = cursor.fetchall()
            # print(total_table_name_of_db)
            # 가져온 테이블명을 돌리면서
            for table in total_table_name_of_db:
                # 셀렉트된 종목코드(?)
                if table[0] == select_combobox_code:
                    df_read = pd.read_sql("SELECT * FROM " + "'" + table[0] + "'", con, index_col=None)
                    # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
                    # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
                    # print(df_read)
                    # df_read.info()
                    # 선택 년월일
                    select_combobox_date = self.comboBox_date_s_day.currentText()
                    if select_combobox_date != '':
                        # 선택시간 기준으로 데이타 수집
                        # print(select_combobox_date)
                        # [당일제외] 체크박스 체크박스가 켜져있으면
                        # 마지막날 데이타는 안가져오고 < / 그렇지 않으면 마지막날 데이타도 가져오고
                        if checkbox_today_x == True:
                            df_read_selected = df_read[df_read['stock_date'] < select_combobox_date]
                        elif checkbox_today_x == False:
                            df_read_selected = df_read[df_read['stock_date'] <= select_combobox_date]
                        # print(df_read_selected)
                        # pd 필요건수 만큼 취하고 역순으로 바꾸기
                        df_read_use = df_read_selected[(stock_price_candle_cnt - 1)::-1]
                        # print(df_read_use)
                        # print(len(df_read_use))
                        # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
                        min_index = df_read_use.index.min()
                    else:
                        # pd 필요건수 만큼 취하고 역순으로 바꾸기
                        df_read_use = df_read[(stock_price_candle_cnt - 1)::-1]
                        # print(df_read_use)
                        # print(len(df_read_use))
                        # 선택시간 기준으로 데이타 수집중에 최소 인덱스 구함
                        min_index = df_read_use.index.min()

                    if stock_price_candle_cnt > len(df_read_use):
                        return
                    # print(min_index)

                    # [당일제외] 체크박스 체크박스가 켜져있으면
                    # 안가져온 마지막 데이타의 시고저종 취하고
                    if checkbox_today_x == True:
                        stock_date = df_read['stock_date'][min_index - 1]
                        run_price = df_read['stock_end'][min_index - 1]
                        start_price = df_read['stock_start'][min_index - 1]
                        high_price = df_read['stock_high'][min_index - 1]
                        low_price = df_read['stock_low'][min_index - 1]
                    # 그렇지 않으면 가져온 마지막 데이타 시고저종 취하고
                    elif checkbox_today_x == False:
                        stock_date = df_read['stock_date'][min_index]
                        run_price = df_read['stock_end'][min_index]
                        start_price = df_read['stock_start'][min_index]
                        high_price = df_read['stock_high'][min_index]
                        low_price = df_read['stock_low'][min_index]
                    # print(run_price)

                    # 차트 그리기
                    self.draw_chart_gui_right(month_or_day, stock_date, df_read_use, min_index, table[0], stock_price_candle_cnt, run_price, start_price, high_price, low_price, checkbox_today_x)
            # db닫기
            con.commit()
            con.close()

    # 당일날 재부팅이면 self.future_s_change 선물 현재값 넣어주고 가기
    def data_pickup_today_rebooting(self):
        # 월물 설정
        current_monthmall = self.current_monthmall_var
        # year 폴더
        folder_name_year = current_monthmall[:4]
        # db명 설정
        db_name = os.getcwd() + '/' + Folder_Name_DB_Store + '/' + folder_name_year + '/' + self.Global_Option_Item_Code_var + '_' + current_monthmall + '.db'
        # db명 존재여부 체크
        is_file = os.path.exists(db_name)
        if is_file == False :
            return

        # 테이블명 설정(오늘날자)
        table_name_today = datetime.datetime.today().strftime("%Y%m%d")
        # print(table_name_today)

        # 테이블명 가져오기
        con = sqlite3.connect(db_name)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name_of_db = cursor.fetchall()
        # print(total_table_name_of_db)
        # 실제 테이블 구하기
        total_table_name = []
        for table in total_table_name_of_db:
            total_table_name.append(table[0])
        # print(total_table_name)

        # 테이블명 설정(오늘날자) 저장된 db에 있으면
        if table_name_today in total_table_name:
            # 데이타 가져오기 함수 호출
            data_pickup_ret = data_pickup(db_name, table_name_today)
            # print(data_pickup_ret)
            max_index = data_pickup_ret.index.max()
            # print(max_index)
            future_s_today_store_data_last = data_pickup_ret['future_s'][max_index - Up_CenterOption_Down]
            # print(future_s_today_store_data_last)
            # print(type(future_s_today_store_data_last))

            # 선물변화 (~%이상)
            self.future_s_change(self.future_s_percent_high, self.future_s_percent_low, future_s_today_store_data_last)
            # 선물 변화 건수 체크
            self.future_s_change_listed_var.append(future_s_today_store_data_last)
        # db닫기
        con.commit()
        con.close()

        # 부팅시 1회 실행::gui 하단에 표시
        self.stock_trend_line_of_ai_day = self.stock_trend_line_of_ai_day_data_fn()
        # 연결선물
        if Chain_Future_s_Item_Code[0] in self.stock_trend_line_of_ai_day['stock_no']:
            for i in range(len(self.stock_trend_line_of_ai_day['stock_no'])):
                if Chain_Future_s_Item_Code[0] == self.stock_trend_line_of_ai_day['stock_no'][i]:
                    # gui 하단에 표시
                    self.future_s_chain_day_poly_max_price_str = str(format(self.stock_trend_line_of_ai_day['poly_sell_max_price'][i], '.2f'))
                    self.future_s_chain_day_poly_min_price_str = str(format(self.stock_trend_line_of_ai_day['poly_buy_min_price'][i], '.2f'))
        else:
            # gui 하단에 표시
            self.future_s_chain_day_poly_max_price_str = ''
            self.future_s_chain_day_poly_min_price_str = ''

    # db 가져오기 함수
    def db_store_pickup(self):
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(Folder_Name_DB_Store)
        if is_store_folder == False:
            return

        # 월물 설정
        current_monthmall = self.current_monthmall_var
        folder_name_year = current_monthmall[:4]
        # db명 설정
        db_name = Folder_Name_DB_Store + '/' + folder_name_year + '/' + self.Global_Option_Item_Code_var + '_' + current_monthmall + '.db'
        # 테이블명 설정
        table_name_today = datetime.datetime.today().strftime("%Y%m%d")

        # 데이타 가져오기 함수 호출
        data_pickup_ret = data_pickup(db_name, table_name_today)







    # 실시간 시세 강도 체크
    def real_time_price_strong(self):
        # 실시간 옵션시세(+-9) 전체카운터
        # 실시간 시세 강도 체크
        self.real_time_total_cnt_accumul.append(self.real_time_total_cnt)
        count_cnt = len(self.real_time_total_cnt_accumul)
        if count_cnt == 2:
            # 현재 실시간 클럭수에서 방금전꺼 뺌
            real_time_count_for_1sec = self.real_time_total_cnt_accumul[-1] - self.real_time_total_cnt_accumul[-2]
            # 초당 실시간 클럭수 최대값 재조정
            if real_time_count_for_1sec > self.real_time_count_for_1sec_max:
                self.real_time_count_for_1sec_max = real_time_count_for_1sec

            del self.real_time_total_cnt_accumul[0]
            # 진행바 표시(최대값 0이 아닐때만 /오류발생)
            if self.real_time_count_for_1sec_max != 0:
                real_time_count_bar_value = (real_time_count_for_1sec * 100) / self.real_time_count_for_1sec_max
                # if real_time_count_bar_value > 100:
                #     real_time_count_bar_value = 100
                self.progressBar_power.setValue(real_time_count_bar_value)

    # 선물변화
    def future_s_change(self, future_s_percent_high, future_s_percent_low, futrue_s_data_run_price):
        # 선물지수 / K200 변화
        self.future_s_run.append(futrue_s_data_run_price)
        future_s_run_cnt = len(self.future_s_run)
        if future_s_run_cnt == 2:
            # 장중이며 선물변화 (0.2%이상) <= 20240207 제외
            # 기조자산 범위
            # Basic_Property_Range = 2.5
            # 기존의 0.1% /0.2% 고민하다가 중심가 변경시를 Basic_Property_Range의 대략 1/3으로 변경하면서 중심가 변경 그의 1/2로 변경
            # 옵션 체결않되는 문제있음... 다시 0.2%로 변경
            if ((self.future_s_run[-2] > (self.future_s_run[-1] * self.future_s_percent_high)) or (
                    self.future_s_run[-2] < (self.future_s_run[-1] * self.future_s_percent_low))):
                # print(future_s_run[-2], future_s_run[-1])
                # print(future_s_run_cnt)
                future_s_run_now = self.future_s_run[-1]
                del self.future_s_run[-2]
                return True, future_s_run_now
            else:
                future_s_run_now = self.future_s_run[-1]
                del self.future_s_run[-1]
                return False, future_s_run_now
        else:
            future_s_run_now = self.future_s_run[-1]
            return False, future_s_run_now

    # 중심가 변경 체크 함수
    def center_option_price_change_check_fn(self):
        # 중심가 함수 호출
        center_index_option_price = self.center_option_price_fn(self.option_price_rows,
                                                                self.output_call_option_data, self.output_put_option_data)
        new_center_index = center_index_option_price[1]
        new_center_option_price = center_index_option_price[2]
        # print(new_center_index)
        # print(new_center_option_price)
        # center_index == 0 경우 패스
        if new_center_index == 0:
            # self.printt('# 중심가 변경 체크 함수')
            # self.printt('if new_center_index == 0:')
            pass
        elif new_center_index != 0:
            # 현재의 중심가와 비교
            if self.center_option_price == new_center_option_price:
                # 중심가 변경 없었음
                pass
            elif self.center_option_price != new_center_option_price:
                # 중심가 변경 되었음
                self.center_index = new_center_index
                self.center_option_price = new_center_option_price
                self.printt('# 중심가 변경 체크 함수')
                self.printt('# 중심가 변경 되었음')
                # 시간표시
                current_time = time.ctime()
                self.printt(current_time)
                self.printt('# 중심가 중심인덱스')
                self.printt(self.center_index)
                self.printt(self.center_option_price)

                # 중심가(45) 함수(차월물) :: 당월물의 중심가와 같은 차월물 인텍스를 찾음
                # 콜옵션 자료와 비교
                for i in range(len(self.output_call_option_data_45['code'])):
                    # str 타입의 당월 중심가와 차월 중심가 비교
                    if self.center_option_price == self.output_call_option_data_45['option_price'][i]:
                        self.center_index_45 = i
                        self.center_option_price_45 = self.output_call_option_data_45['option_price'][i]
                self.printt('# 차월물 중심가 중심인덱스')
                self.printt(self.center_index_45)
                self.printt(self.center_option_price_45)

                # 선옵 잔고확인 버튼 변수 True
                if self.myhave_option_button_var == True:
                    # 중심가 변경시
                    self.printt('# 중심가 변경시')
                    self.option_s_center_index_change_ready()

    # 중심가 함수(부팅시에는 조정델타 없이 처리)
    def center_option_price_for_booting_fn(self, option_price_rows, call_data, put_data):
        # 변수 초기화
        center_index = 0
        center_option_price = ''
        for i in range(option_price_rows - 2):
            if put_data['Delta'][i + 0] * put_data['Delta'][i + 1] * put_data['Delta'][i + 2] * \
                    call_data['Delta'][i + 2] * call_data['Delta'][i + 1] * call_data['Delta'][i + 0] == 0:
                # 비교금액 6 delta중 1금액이라도 0이면 다음으로 이동
                continue

            # 비교 조정 delta 반대편 2 delta 3등분으로 함
            # 가격 말고 delta로 변경(20240207) <= 더 정확함
            put_adj_delta = 0
            # delta는 중심가 근처에서 간격당 20씩임 그래서 4로 나눠서
            put_adj_delta_up = put_data['Delta'][i] - put_adj_delta
            put_adj_delta_dn = put_data['Delta'][i + 2] + put_adj_delta
            # 콜의 상대편 풋비교 조정delta보다 작거나 크거나
            if (put_adj_delta_up > call_data['Delta'][i + 1]) and (call_data['Delta'][i + 1] > put_adj_delta_dn):

                # 비교 조정 delta 반대편 2 delta 3등분으로 함
                # 가격 말고 delta로 변경(20240207) <= 더 정확함
                call_adj_delta = 0
                # delta는 중심가 근처에서 간격당 20씩임 그래서 4로 나눠서
                call_adj_price_up = call_data['Delta'][i + 2] - call_adj_delta
                call_adj_price_dn = call_data['Delta'][i] + call_adj_delta
                # 풋의 상대편 콜비교 조정delta보다 작거나 크거나
                if (call_adj_price_up > put_data['Delta'][i + 1]) and (put_data['Delta'][i + 1] > call_adj_price_dn):

                    # 중심가 생성
                    center_index = i + 1
                    center_option_price = call_data['option_price'][i + 1]
                    # print(center_index)
                    # print(center_option_price)
                    return True, center_index, center_option_price
        return False, center_index, center_option_price

    # 중심가 함수
    def center_option_price_fn(self, option_price_rows, call_data, put_data):
        # 변수 초기화
        center_index = 0
        center_option_price = ''
        for i in range(option_price_rows - 2):
            if put_data['Delta'][i + 0] * put_data['Delta'][i + 1] * put_data['Delta'][i + 2] * \
                    call_data['Delta'][i + 2] * call_data['Delta'][i + 1] * call_data['Delta'][i + 0] == 0:
                # 비교금액 6 delta중 1금액이라도 0이면 다음으로 이동
                continue

            # 비교 조정 delta 반대편 2 delta 3등분으로 함
            # 가격 말고 delta로 변경(20240207) <= 더 정확함
            put_adj_delta = (put_data['Delta'][i] - put_data['Delta'][i + 2]) / 4
            # delta는 중심가 근처에서 간격당 20씩임 그래서 4로 나눠서
            put_adj_delta_up = put_data['Delta'][i] - put_adj_delta
            put_adj_delta_dn = put_data['Delta'][i + 2] + put_adj_delta
            # 콜의 상대편 풋비교 조정delta보다 작거나 크거나
            if (put_adj_delta_up > call_data['Delta'][i + 1]) and (call_data['Delta'][i + 1] > put_adj_delta_dn):

                # 비교 조정 delta 반대편 2 delta 3등분으로 함
                # 가격 말고 delta로 변경(20240207) <= 더 정확함
                call_adj_delta = (call_data['Delta'][i + 2] - call_data['Delta'][i]) / 4
                # delta는 중심가 근처에서 간격당 20씩임 그래서 4로 나눠서
                call_adj_price_up = call_data['Delta'][i + 2] - call_adj_delta
                call_adj_price_dn = call_data['Delta'][i] + call_adj_delta
                # 풋의 상대편 콜비교 조정delta보다 작거나 크거나
                if (call_adj_price_up > put_data['Delta'][i + 1]) and (put_data['Delta'][i + 1] > call_adj_price_dn):

                    # 중심가 생성
                    center_index = i + 1
                    center_option_price = call_data['option_price'][i + 1]
                    # print(center_index)
                    # print(center_option_price)
                    return True, center_index, center_option_price
        return False, center_index, center_option_price

    # 중심가(45) 함수(차월물) :: 당월물의 중심가와 같은 차월물 인텍스를 찾음
    def center_option_price_45_fn(self, center_option_price, call_data_45, put_data_45):
        # 변수선언
        center_call_index_45 = 0
        center_call_option_price_45 = ''
        center_put_index_45 = 0
        center_put_option_price_45 = ''
        center_index_45 = 0
        center_option_price_45 = 0
        for c in range(len(call_data_45['code'])):
            if center_option_price == call_data_45['option_price'][c]:
                center_call_index_45 = c
                center_call_option_price_45 = call_data_45['option_price'][c]
                print(center_call_index_45)
                print(center_call_option_price_45)

        for p in range(len(put_data_45['code'])):
            if center_option_price == put_data_45['option_price'][p]:
                center_put_index_45 = p
                center_put_option_price_45 = call_data_45['option_price'][p]
                print(center_put_index_45)
                print(center_put_option_price_45)

        if (center_call_index_45 == center_put_index_45) and (center_call_option_price_45 == center_put_option_price_45) \
                and (center_call_index_45 != 0) and (center_put_index_45 != 0):
            center_index_45 = center_call_index_45
            center_option_price_45 = center_call_option_price_45

            return True, center_index_45, center_option_price_45

        else:

            return False, center_index_45, center_option_price_45

    # text_data_store_trans
    def printt(self, store_data):
        # 영업일 기준 str ''이 아닐때 실행
        if self.day_residue_str != '':
            txt_file_store(Folder_Name_TXT_Store, self.Global_Option_Item_Code_var, self.day_residue_str,
                           store_data)
        else:
            print(store_data)

    # text_data_store_trans
    def printt_buyed(self, store_data):
        # 영업일 기준 str ''이 아닐때 실행
        if self.day_residue_str != '':
            txt_file_store(Folder_Name_TXT_Store, File_Kind_Buy, self.day_residue_str, store_data)
    # text_data_store_trans
    def printt_selled(self, store_data):
        # 영업일 기준 str ''이 아닐때 실행
        if self.day_residue_str != '':
            txt_file_store(Folder_Name_TXT_Store, File_Kind_Sell, self.day_residue_str, store_data)


    # 60초 한번씩 클럭 발생 :: 콜/풋 월별시세요청
    def timer_empty_fn(self):
        # 60초 한번씩 클럭 발생 :: 콜/풋 월별시세요청
        self.printt('60초 경과 # 선물전체시세요청 # 콜/풋 월별시세요청 실행')
        # 인스턴스 변수 선언
        self.futrue_s_reset_output()
        # 인스턴스 변수 선언
        self.option_reset_output()

        # 콜/풋 월별시세요청
        self.call_put_data_rq()
        # 선물전체시세요청
        self.futrue_s_data_rq()

        # stock / option 계좌선택(중심가 하나라도 없을경우)
        # stock_accountrunVar
        stock_accountrunVar = self.comboBox_acc_stock.currentText()
        # option_accountrunVar
        option_accountrunVar = self.comboBox_acc.currentText()
        if stock_accountrunVar != option_accountrunVar:
            # 계좌선택 이후 선옵잔고요청 가능
            self.pushButton_myhave.setEnabled(True)
            # 계좌선택 이후 자동주문 클릭 가능
            self.pushButton_auto_order.setEnabled(True)

        # 중심 인텍스가 제로 아닐때
        if (self.center_index != 0) and (self.center_index_45 != 0):
            # # 차월물 중심가 인덱스 존재하고 중심가가 같을때 실행함(차월물과 당월물의 차이가 비슷할때)
            # if self.center_option_price == self.center_option_price_45:
            # 중심가 생성 타이머 중지
            self.timer_empty.stop()
            self.printt('당월물 차월물 중심가 인덱스 생성 :: timer_empty 중지')
            # 중심가 생성 1초 타이머 재시작
            self.timer1.start(Future_s_Leverage_Int * 100)
            self.printt('당월물 차월물 중심가 인덱스 생성 :: timer1 재시작')

    # 1초에 한번씩 클럭 발생
    def timer1sec(self):
        # 실시간 이벤트 처리 가능여부 변수
        self.receive_real_data_is_OK = True

        # -----
        # 중심가 변경 체크 함수
        self.center_option_price_change_check_fn()
        # 장시작 최초 center_index == 0 경우 예측
        # 차월물 중심가 인덱스 존재하고 중심가가 같을때 실행함(차월물과 당월물의 차이가 비슷할때)
        if (self.center_index == 0) or (self.center_index_45 == 0):
            # or (self.center_option_price != self.center_option_price_45):
            self.printt('if (self.center_index == 0) or (self.center_index_45 == 0):')
            # / 차월물 중심가 다름')
            # 타이머 중지
            self.timer1.stop()
            self.printt('timer1 타이머 중지')
            # 60초 한번씩 클럭 발생 :: 콜/풋 월별시세요청
            self.timer_empty.start(1000 * 60)
            self.printt('timer_empty 타이머 시작')
            return
        # -----

        # stock / option 계좌선택
        # stock_accountrunVar
        stock_accountrunVar = self.comboBox_acc_stock.currentText()
        # option_accountrunVar
        option_accountrunVar = self.comboBox_acc.currentText()
        if stock_accountrunVar != option_accountrunVar:
            # 계좌선택 이후 선옵잔고요청 가능
            self.pushButton_myhave.setEnabled(True)
            # 계좌선택 이후 자동주문 클릭 가능
            self.pushButton_auto_order.setEnabled(True)

        # 현재 주문변수 현황표시
        if len(self.item_list_cnt_type['code_no']) == 0:
            # 진행바 표시(주문중 아님)
            self.progressBar_order.setValue(0)
            # 방금전 "체결"이 매도 혹은 매수 체크하여
            # 매도 였으면 매수먼저
            # 최초 부팅시에 self.last_order_sell_or_buy 는 1로 처리
            self.last_order_sell_or_buy = 1
            # 초기화
        elif len(self.item_list_cnt_type['code_no']) != 0:
            # 진행바 표시(주문중)
            self.progressBar_order.setValue(100)

        # -----
        # 일단 옵션재고는 매도만 있다고 가정하고
        # 선물재고와 옵션재고 비교하면서 옵션 주문은 1건씩만 처리(x)
        # 선물 주문처리도 1건씩만
        myhave_future_s_sell_delta_sum = 0
        myhave_future_s_buy_delta_sum = 0

        # -----
        # 선물 재고의 'Delta' 구하기
        for mh in range(len(self.option_myhave['code'])):
            # 선물이면서
            if self.option_myhave['code'][mh][:3] == '101':
                # 선물 매도 재고
                if self.option_myhave['sell_or_buy'][mh] == 1:
                    if self.option_myhave['myhave_cnt'][mh] > 0:
                        myhave_future_s_sell_delta_sum += abs(self.option_myhave['myhave_cnt'][mh] * 100)
                # 선물 매수 재고
                elif self.option_myhave['sell_or_buy'][mh] == 2:
                    if self.option_myhave['myhave_cnt'][mh] > 0:
                        myhave_future_s_buy_delta_sum += abs(self.option_myhave['myhave_cnt'][mh] * 100)
        myhave_future_s_total_delta_sum = myhave_future_s_sell_delta_sum + myhave_future_s_buy_delta_sum
        # -----

        # -----
        # 선물 옵션 주문 던지기
        # self.printt('# 선물 옵션 주문 던지기 timer1 중지')
        # state : 0(선택), 1(주문), 2(취소), 3(체결-삭제)
        # 주문순서 : 선물 => 옵션매수 => 옵션매도 => 나머지
        # 선물
        # 선물 먼저
        # 최종 결과 - 선물 동시에 몽땅(x) :: 선물도 1건씩만
        if (self.futrue_s_data['item_code'][0] in self.item_list_cnt_type['code_no']) or (self.futrue_s_data_45['item_code'][0] in self.item_list_cnt_type['code_no']):
            # 선물 주문중인지 판단 변수(주문변수에 당월물 차월물 종목코드 있으면~~)
            # self.future_s_ordering = True 일경우에는 옵션관련 선물관련 함수 미 실행
            self.future_s_ordering = True
            item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
            # 0(선택) 있으면서 / 1(주문) 여부와 상관없이(옵션 1(주문) 무시)
            if 0 in self.item_list_cnt_type['state']:
                # 종목코드 기준으로 돌리면서
                for i in range(len(self.item_list_cnt_type['code_no'])):
                    # 선물 확인
                    if self.item_list_cnt_type['code_no'][i][:3] == '101':
                        # 주문상태 0(선택) 확인
                        if self.item_list_cnt_type['state'][i] == 0:
                            # 건수 확인
                            if self.item_list_cnt_type['cnt'][i] > 0:

                                # -----
                                item_list_cnt_type['code_no'].append(self.item_list_cnt_type['code_no'][i])
                                # 선물도 주문처리는 1건씩만
                                item_list_cnt_type['cnt'].append(self.order_cnt_onetime)
                                item_list_cnt_type['sell_buy_type'].append(self.item_list_cnt_type['sell_buy_type'][i])
                                # state : 1(주문) 변경
                                self.item_list_cnt_type['state'][i] = 1
                # 주문 던지기
                # 검색된 종목코드 여부
                item_list_cnt = len(item_list_cnt_type['code_no'])
                if item_list_cnt > 0:
                    self.future_s_market_sell_buy(item_list_cnt_type)
                    self.printt('self.item_list_cnt_type - "timer1sec" # 선물 먼저')
                    self.printt(self.item_list_cnt_type)
                    # break
                    # 혹시 차월물이 있을경우를 대비해서 # break 주석처리
                                # -----
        else:
            # 선물 주문중인지 판단 변수(주문변수에 당월물 차월물 종목코드 있으면~~)
            # self.future_s_ordering = True 일경우에는 옵션관련 선물관련 함수 미 실행
            self.future_s_ordering = False

        # 옵션
        # 0(선택) 있으면서 1(주문) 없고
        if 0 in self.item_list_cnt_type['state']:
            if 1 not in self.item_list_cnt_type['state']:
                # 종목코드 기준으로 돌리면서
                for i in range(len(self.item_list_cnt_type['code_no'])):
                    # 주문상태 0(선택) 확인
                    if self.item_list_cnt_type['state'][i] == 0:
                        # 건수 확인
                        if self.item_list_cnt_type['cnt'][i] > 0:

                            # -----
                            # 옵션 만기일 처리
                            day_residue_int = self.output_put_option_data['day_residue'][self.center_index]  # int
                            # 2: 장종료전 일경우에 당월몰 주문 예외
                            # 장마감 self.MarketEndingVar == '2'
                            # 장마감 2 이후
                            if (day_residue_int == 1) and (self.MarketEndingVar == '2'):
                                if self.item_list_cnt_type['code_no'][i] in self.output_call_option_data['code']:
                                    # 옵션 만기일이고 장마감 2 이후 당월물은
                                    # 리스트에서 삭제
                                    del self.item_list_cnt_type['code_no'][i]
                                    del self.item_list_cnt_type['cnt'][i]
                                    del self.item_list_cnt_type['sell_buy_type'][i]
                                    del self.item_list_cnt_type['state'][i]
                                    del self.item_list_cnt_type['order_no'][i]
                                    self.printt('# 옵션 만기일이고 장마감 2 이후 당월물은 리스트에서 삭제')
                                    break  # 리스트 요소를 삭제하였으므로 for문 중지
                                if self.item_list_cnt_type['code_no'][i] in self.output_put_option_data['code']:
                                    # 옵션 만기일이고 장마감 2 이후 당월물은
                                    # 리스트에서 삭제
                                    del self.item_list_cnt_type['code_no'][i]
                                    del self.item_list_cnt_type['cnt'][i]
                                    del self.item_list_cnt_type['sell_buy_type'][i]
                                    del self.item_list_cnt_type['state'][i]
                                    del self.item_list_cnt_type['order_no'][i]
                                    self.printt('# 옵션 만기일이고 장마감 2 이후 당월물은 리스트에서 삭제')
                                    break  # 리스트 요소를 삭제하였으므로 for문 중지
                            # -----

                            # 최종 결과
                            item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}

                            # -----
                            # 선물재고와 옵션재고 비교하면서 옵션 주문은 1건씩만 처리(x)
                            # 옵션의 델타가 선물의 델타보다 클때 [옵션청산(매수)]
                            # 위처럼 하려 하였는데 그럼 매도건수가 너무 많이 증가하여 증거금 부족이 나올수도 있다는 우려때문에

                            # -----
                            # 방금전 "체결"이 매도 혹은 매수 체크하여
                            # 매도 였으면 매수먼저
                            # 매수 였으면 매도먼저
                            # 최초 부팅시에 self.last_order_sell_or_buy 는 1로 처리
                            if self.last_order_sell_or_buy == 2:
                                # 매도 차례
                                if 1 in self.item_list_cnt_type['sell_buy_type']:
                                    # 매도 처리
                                    if self.item_list_cnt_type['sell_buy_type'][i] == 1:
                                        self.printt('# 방금전 "체결"이 매수 였으면 매도 먼저')
                                        self.printt(self.last_order_sell_or_buy)
                                        item_list_cnt_type['code_no'].append(self.item_list_cnt_type['code_no'][i])
                                        # 옵션 주문처리는 1건씩만
                                        item_list_cnt_type['cnt'].append(self.order_cnt_onetime)
                                        item_list_cnt_type['sell_buy_type'].append(
                                            self.item_list_cnt_type['sell_buy_type'][i])
                                        # 상태를 1(주문) 변경
                                        self.item_list_cnt_type['state'][i] = 1
                                        # 주문 던지기
                                        # 검색된 종목코드 여부
                                        item_list_cnt = len(item_list_cnt_type['code_no'])
                                        if item_list_cnt > 0:
                                            self.future_s_market_sell_buy(item_list_cnt_type)
                                            break
                                else:
                                    # 매수 처리
                                    if self.item_list_cnt_type['sell_buy_type'][i] == 2:
                                        self.printt('# 방금전 "체결"이 매수 였으나 매도 없어서 매수 처리')
                                        self.printt(self.last_order_sell_or_buy)
                                        item_list_cnt_type['code_no'].append(self.item_list_cnt_type['code_no'][i])
                                        # 옵션 주문처리는 1건씩만
                                        item_list_cnt_type['cnt'].append(self.order_cnt_onetime)
                                        item_list_cnt_type['sell_buy_type'].append(
                                            self.item_list_cnt_type['sell_buy_type'][i])
                                        # 상태를 1(주문) 변경
                                        self.item_list_cnt_type['state'][i] = 1
                                        # 주문 던지기
                                        # 검색된 종목코드 여부
                                        item_list_cnt = len(item_list_cnt_type['code_no'])
                                        if item_list_cnt > 0:
                                            self.future_s_market_sell_buy(item_list_cnt_type)
                                            break

                            elif self.last_order_sell_or_buy == 1:
                                # 매수 차례
                                if 2 in self.item_list_cnt_type['sell_buy_type']:
                                    # 매수 처리
                                    if self.item_list_cnt_type['sell_buy_type'][i] == 2:
                                        self.printt('# 방금전 "체결"이 매도 였으면 매수 먼저')
                                        self.printt(self.last_order_sell_or_buy)
                                        item_list_cnt_type['code_no'].append(self.item_list_cnt_type['code_no'][i])
                                        # 옵션 주문처리는 1건씩만
                                        item_list_cnt_type['cnt'].append(self.order_cnt_onetime)
                                        item_list_cnt_type['sell_buy_type'].append(
                                            self.item_list_cnt_type['sell_buy_type'][i])
                                        # 상태를 1(주문) 변경
                                        self.item_list_cnt_type['state'][i] = 1
                                        # 주문 던지기
                                        # 검색된 종목코드 여부
                                        item_list_cnt = len(item_list_cnt_type['code_no'])
                                        if item_list_cnt > 0:
                                            self.future_s_market_sell_buy(item_list_cnt_type)
                                            break
                                else:
                                    # 매도 처리
                                    if self.item_list_cnt_type['sell_buy_type'][i] == 1:
                                        self.printt('# 방금전 "체결"이 매도 였으나 매수건 없어서 매도 처리')
                                        self.printt(self.last_order_sell_or_buy)
                                        item_list_cnt_type['code_no'].append(self.item_list_cnt_type['code_no'][i])
                                        # 옵션 주문처리는 1건씩만
                                        item_list_cnt_type['cnt'].append(self.order_cnt_onetime)
                                        item_list_cnt_type['sell_buy_type'].append(
                                            self.item_list_cnt_type['sell_buy_type'][i])
                                        # 상태를 1(주문) 변경
                                        self.item_list_cnt_type['state'][i] = 1
                                        # 주문 던지기
                                        # 검색된 종목코드 여부
                                        item_list_cnt = len(item_list_cnt_type['code_no'])
                                        if item_list_cnt > 0:
                                            self.future_s_market_sell_buy(item_list_cnt_type)
                                            break
                            # -----

                self.printt('self.item_list_cnt_type - "timer1sec" # 옵션')
                self.printt(self.item_list_cnt_type)
        # -----

        # -----
        # 지난 옵션 헤지 비율 가져오기
        last_option_s_hedge_ratio = self.option_s_hedge_ratio_pickup_fn()
        # self.option_s_hedge_ratio [0%/100%, 50%/100%, 66%/100%]
        # 만약 파일이 없거나 아직 저장된적이 없으면 default : 100

        # 선물(진입/청산) 신호발생 db 호출
        center_option_price_db_last = self.center_option_price_db_last_fn()
        float_center_option_price_db_last = float(center_option_price_db_last)
        float_center_option_price = float(self.center_option_price)
        # print(float_center_option_price_db_last)
        # print(float_center_option_price)
        # -----

        # -----
        # 선물 바스켓 가져오기
        basket_cnt = self.future_s_basket_cnt_text_read()
        # -----

        # 매수/매도 준비
        self.stock_trend_line_of_ai_day = self.stock_trend_line_of_ai_day_data_fn()

        # -----
        # 연결선물
        if Chain_Future_s_Item_Code[0] in self.stock_trend_line_of_ai_day['stock_no']:
            for i in range(len(self.stock_trend_line_of_ai_day['stock_no'])):
                if Chain_Future_s_Item_Code[0] == self.stock_trend_line_of_ai_day['stock_no'][i]:
                    # gui 하단에 표시
                    self.future_s_chain_day_poly_max_price_str = str(
                        format(self.stock_trend_line_of_ai_day['poly_sell_max_price'][i], '.2f'))
                    self.future_s_chain_day_poly_min_price_str = str(
                        format(self.stock_trend_line_of_ai_day['poly_buy_min_price'][i], '.2f'))
        else:
            # GUI 하단에 표시용
            self.future_s_chain_day_poly_max_price_str = ''
            self.future_s_chain_day_poly_min_price_str = ''
        # -----

        # 시분초 : db 중복 시분 제외 변수선언
        current_time = QTime.currentTime()
        db_overlap_time_except = current_time.toString('hh:mm')
        if db_overlap_time_except != self.db_overlap_time_list[-1]:
            # 선물변화 프로세스 실행중 여부
            self.future_s_change_running = True
            # 선물변화 (~%이상)
            future_s_change_ret = self.future_s_change(self.future_s_percent_high, self.future_s_percent_low, self.futrue_s_data['run_price'][0])
            if future_s_change_ret[0] == True:
                # 시간표시
                current_time = datetime.datetime.now()
                # print(current_time)
                # print(current_time.time())
                # index_text_time = current_time.toString('hh:mm')
                store_time_var = current_time.time()
                # current_time = time.ctime()
                self.printt('# -----')
                self.printt(store_time_var)
                # 시분초 : db 중복 시분 제외 변수선언
                self.db_overlap_time_list.append(db_overlap_time_except)
                self.printt('self.db_overlap_time_list')
                self.printt(self.db_overlap_time_list)
                self.printt('future_s_change_ret')
                self.printt(future_s_change_ret)
                # 선물 변화 건수 체크
                self.future_s_change_listed_var.append(future_s_change_ret[1])
                self.printt('# self.future_s_change_listed_var')
                self.printt(len(self.future_s_change_listed_var))
                self.printt(self.future_s_change_listed_var)
                # True 인식과 동시에 저장함수 데이터 바인딩
                output_call_option_data = self.output_call_option_data
                output_put_option_data = self.output_put_option_data


                # # slow 교차::선물변화시 center_index있으면 가장 먼저 실행해야함
                # self.slow_cross_check_shift()
                # # self.printt('self.slow_cmp_call + self.slow_cmp_put')
                # # self.printt(self.slow_cmp_call)
                # # self.printt(self.slow_cmp_put)
                # # 교차체크전송 함수 호출
                # self.slow_cross_check_trans()

                # 흐름변경 :: stock_delta / favorites_deal_power chart view
                # 저장함수
                self.data_store_ready(store_time_var, output_call_option_data, output_put_option_data)

                # -----
                # 일봉
                # 매도 최고가 / 매수 최고가
                self.printt('# stock_trend_line_of_ai_day_data_fn(self):')
                self.printt('# self.stock_trend_line_of_ai_day')
                self.printt(self.stock_trend_line_of_ai_day)
                # -----

                # -----
                # 주식 매도/매수는 종목추가전에 체크
                # 선물 옵션은 미리 미리 체크
                # 당일 매도 종목 찾기
                self.selled_today_items = self.selled_today_items_search_fn()
                self.printt('# 당일 매도 종목 찾기')
                self.printt(self.selled_today_items)
                # 당일 매수 종목 찾기
                self.buyed_today_items = self.buyed_today_items_search_fn()
                self.printt('# 당일 매수 종목 찾기')
                self.printt(self.buyed_today_items)
                # -----

                # -----
                # 1: 국내주식 잔고통보, 4: 파생상품 잔고통보
                self.printt('1: 국내주식 잔고통보, 4: 파생상품 잔고통보 :: 결과 확인용')
                self.printt('self.option_myhave')
                self.printt(self.option_myhave)
                self.printt('self.stock_have_data')
                self.printt(self.stock_have_data)
                # -----

                # -----
                # 주식 매수 종목
                stock_tarket_item_list = []
                for i in range(len(self.stock_trend_line_of_ai_day['stock_no'])):
                    for k in range(len(self.stock_item_data['stock_item_no'])):
                        if self.stock_trend_line_of_ai_day['stock_no'][i] == self.stock_item_data['stock_item_no'][k]:
                            if self.stock_trend_line_of_ai_day['poly_buy_min_price'][i] > \
                                    self.stock_item_data['stock_end'][k]:
                                if self.stock_item_data['stock_item_no'][k] not in self.buyed_today_items:
                                    stock_tarket_item_list.append(self.stock_item_data['stock_item_no'][k])
                # -----

                # #  -----
                # # 장마감 c_to_cf_hand <= 변경해서 실시간 db만 저장하는것으로
                # self.c_to_cf_realtime()
                # # -----
                # 당일의 고/저 확인되지 않았는데 매매는 오류를 발생 <= 월봉으로 거래를 하지 않는것과 같은 개념(20240205)

                # -----
                # 타이머 중지
                self.timer1.stop()
                self.printt('stock_buy_items_search / future_s_market_ready / option_s_delta_tuning_fn 시작 timer1 중지')
                # 선옵 잔고확인 버튼 변수 True
                if self.myhave_option_button_var == True:
                    # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
                    if self.MarketEndingVar == '3':
                        # 주식매수 종목검색
                        self.stock_buy_items_search(stock_tarket_item_list)
                # 선물 주문중인지 판단 변수(주문변수에 당월물 차월물 종목코드 있으면~~)
                # self.future_s_ordering = True 일경우에는 옵션관련 선물관련 함수 미 실행
                if self.future_s_ordering == False:
                    # 자동주문 버튼 True
                    if self.auto_order_button_var == True:
                        # 옵션 델타 튜닝 = > 항상 현재에 맞춰서
                        self.option_s_delta_tuning_fn(float_center_option_price, float_center_option_price_db_last, basket_cnt)
                        # 옵션 델타 튜닝 함수에 접수안된건 삭제 기능이 있으므로 선물 준비보다 먼저 실행
                        # 선물 (진입/청산) 준비
                        self.future_s_market_ready(last_option_s_hedge_ratio, basket_cnt)
                # 타이머 시작
                self.timer1.start(Future_s_Leverage_Int * 100)
                self.printt('stock_buy_items_search / future_s_market_ready / option_s_delta_tuning_fn 시작 timer1 재시작')
                # -----

                # 옵션거래 [실시간 조회] 체크박스가 켜져있을때만
                if self.checkbox_realtime.isChecked():
                    # 선물 변화 건수 체크
                    future_s_change_cnt = len(self.future_s_change_listed_var)
                    if future_s_change_cnt >= 1:
                        # 가저오기 함수
                        self.data_pickup_1sec()
            else:
                # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
                if self.MarketEndingVar == '3':
                    # 옵션거래 [실시간 조회] 체크박스가 켜져있을때만
                    if self.checkbox_realtime.isChecked():
                        # 선물 변화 건수 체크
                        future_s_change_cnt = len(self.future_s_change_listed_var)

            # 선물변화 프로세스 실행중 여부
            self.future_s_change_running = False

        # 시분초
        current_time = QTime.currentTime()
        text_time = current_time.toString('hh:mm:ss')
        time_msg = text_time
        # 서버접속 체크
        state = self.kiwoom.get_connect_state()
        if state == 1:
            state_msg = 'OnLine'
        else:
            state_msg = 'OffLine'

        # 선물 변화 건수 체크
        # self.future_s_change_listed_var.append(future_s_change_ret[1])
        # self.printt(self.future_s_change_listed_var)
        future_s_change_cnt = len(self.future_s_change_listed_var)
        # GUI 하단에 표시용 항목들의 대부분을 부팅시 혹은 초단위 함수에서 거의 가져옴으로서 >= 0으로 변경
        if future_s_change_cnt >= 0:
            # 장운영구분
            MarketEndingVar_view = '장운영 ' + self.MarketEndingVar
            # 보유종목수
            stock_have_cnt = len(self.stock_have_data['stock_no'])
            stock_have_cnt_text = str(stock_have_cnt)
            stock_have_cnt_view = 'STOCK보유 ' + stock_have_cnt_text
            # 영업일 기준 잔존일
            day_residue_text = '옵션잔존일 ' + self.day_residue_str
            future_s_day_residue_text = '선물잔존일 ' + self.future_s_day_residue_str

            # 실시간 시세 강도 체크
            self.real_time_price_strong()
            # 실시간 옵션시세(+-9) 카운터
            real_time_total_cnt = str(format(self.real_time_total_cnt, ','))
            real_time_count_for_1sec_max = str(format(self.real_time_count_for_1sec_max, ','))
            real_time_total_cnt_text = '실시간카운터 ' + real_time_total_cnt + '(' + real_time_count_for_1sec_max + ')'

            # 중심가 중심인텍스 표시
            center_option_price_text = '중심가 ' + str(self.center_option_price) +\
                                       '(차 ' + str(self.center_option_price_45) + ')'
            center_index_text = '중심인덱스 ' + str(self.center_index) + '(차 ' + str(self.center_index_45) + ')'

            # 옵션 전체 건수
            option_s_total_cnt_text = '옵션전체건수 ' + str(self.option_price_rows)
            # last_option_s_hedge_ratio [0%/100%, 50%/100%, 66%/100%]
            option_s_hedge_ratio_text = '옵션헤지비율 ' + str(last_option_s_hedge_ratio)
            # 지난 진입시 중심가(GUI 하단에 표시용)
            center_option_price_db_last_text = '지난진입중심가 ' + str(center_option_price_db_last)
            # 선물 바스켓
            basket_cnt_text = '바스켓 ' + str(basket_cnt)

            # 연결선물 정보
            future_s_chain_info_text = '연결선물 ' + 'P(' + \
                                       self.future_s_chain_day_poly_max_price_str + '/' + \
                                       self.future_s_chain_day_poly_min_price_str + ')'
            # 선물
            future_s_run_text = '선물 ' + str(format(self.futrue_s_data['run_price'][0], '.2f'))

            self.statusbar.showMessage(self.accouns_id + '(' + self.accounts_name + ')' + ' | ' + state_msg +
                                       '(' + time_msg + ')' + ' | ' + future_s_run_text + ' | ' +
                                       future_s_chain_info_text + ' | ' +
                                       option_s_hedge_ratio_text + ' | ' +
                                       center_option_price_db_last_text + ' | ' +
                                       center_option_price_text + ' | ' +
                                       center_index_text + ' | ' +
                                       basket_cnt_text + ' | ' +
                                       option_s_total_cnt_text + ' | ' +
                                       stock_have_cnt_view + ' | ' + day_residue_text + ' | ' +
                                       future_s_day_residue_text + ' | ' + MarketEndingVar_view)
        else:
            self.statusbar.showMessage(self.accouns_id + '(' + self.accounts_name + ')' + ' | ' +
                                       state_msg + '(' + time_msg + ')')

        # -----
        # 버튼에 표기
        # 색상 입히기 전에 모두 흰색으로
        self.pushButton_fu_buy_have.setStyleSheet('background-color: rgb(255, 255, 255)')
        self.pushButton_fu_sell_have.setStyleSheet('background-color: rgb(255, 255, 255)')
        self.pushButton_callhave.setStyleSheet('background-color: rgb(255, 255, 255)')
        self.pushButton_puthave.setStyleSheet('background-color: rgb(255, 255, 255)')
        # 색상 및 텍스트
        for i in range(len(self.option_myhave['code'])):
            # print(self.option_myhave['code'][i][:3])
            if self.option_myhave['code'][i][:3] == '101':
                if self.option_myhave['sell_or_buy'][i] == 2:
                    self.pushButton_fu_buy_have.setStyleSheet('background-color: rgb(255, 0, 0)')
                    self.pushButton_fu_buy_have.setText(self.option_myhave['code'][i])
                elif self.option_myhave['sell_or_buy'][i] == 1:
                    self.pushButton_fu_sell_have.setStyleSheet('background-color: rgb(0, 0, 255)')
                    self.pushButton_fu_sell_have.setText(self.option_myhave['code'][i])
            elif self.option_myhave['code'][i][:3] == '201':
                if self.option_myhave['sell_or_buy'][i] == 2:
                    self.pushButton_callhave.setStyleSheet('background-color: rgb(127, 0, 127)')
                    self.pushButton_callhave.setText(self.option_myhave['code'][i])
                elif self.option_myhave['sell_or_buy'][i] == 1:
                    self.pushButton_callhave.setStyleSheet('background-color: rgb(255, 0, 255)')
                    self.pushButton_callhave.setText(self.option_myhave['code'][i])
            elif self.option_myhave['code'][i][:3] == '301':
                if self.option_myhave['sell_or_buy'][i] == 2:
                    self.pushButton_puthave.setStyleSheet('background-color: rgb(0, 127, 127)')
                    self.pushButton_puthave.setText(self.option_myhave['code'][i])
                elif self.option_myhave['sell_or_buy'][i] == 1:
                    self.pushButton_puthave.setStyleSheet('background-color: rgb(0, 255, 255)')
                    self.pushButton_puthave.setText(self.option_myhave['code'][i])
        # -----

        # -----
        # 버튼에 표기
        # 장시작 3
        if self.MarketEndingVar == '3':
            self.pushButton_market_start_3.setStyleSheet('background-color: rgb(128, 0, 128)')
            self.pushButton_market_start_3.setText(self.MarketEndingVar)
        else:
            self.pushButton_market_start_3.setStyleSheet('background-color: rgb(255, 255, 255)')
            self.pushButton_market_start_3.setText('3: 장시작(Hand)')
        # 장마감 c
        if self.MarketEndingVar == 'c':
            self.pushButton_market_ending_c.setStyleSheet('background-color: rgb(147, 112, 219)')
            self.pushButton_market_ending_c.setText(self.MarketEndingVar)
        # 장마감 cf
        elif self.MarketEndingVar == 'cf':
            self.pushButton_market_ending_c.setStyleSheet('background-color: rgb(128, 0, 128)')
            self.pushButton_market_ending_c.setText(self.MarketEndingVar)
        else:
            self.pushButton_market_ending_c.setStyleSheet('background-color: rgb(255, 255, 255)')
            self.pushButton_market_ending_c.setText('c: 장마감(Hand)')
        # -----

        # 선물 롤오버
        # 장마감 self.MarketEndingVar == '2'
        if self.MarketEndingVar == '2':
            # 장마감 2 이후
            # 선물 롤오버 1번실행

            # -----
            # 당일날 선물 롤오버 없었을 경우에만
            if self.future_s_roll_over_run_var == False:
                # 선물 주문중인지 판단 변수(주문변수에 당월물 차월물 종목코드 있으면~~)
                # self.future_s_ordering = True 일경우에는 옵션관련 선물관련 함수 미 실행
                if self.future_s_ordering == False:
                    # 자동주문 버튼 True
                    if self.auto_order_button_var == True:
                        # 타이머 중지
                        self.timer1.stop()
                        self.printt('future_s_roll_over_fn / option_s_delta_tuning_fn 시작 timer1 중지')
                        # 옵션 델타 튜닝 = > 항상 현재에 맞춰서
                        self.option_s_delta_tuning_fn(float_center_option_price, float_center_option_price_db_last, basket_cnt)
                        # 옵션 델타 튜닝 함수에 접수안된건 삭제 기능이 있으므로 선물 준비보다 먼저 실행
                        # 선물 (진입/청산) 준비
                        self.future_s_roll_over_fn(basket_cnt)
                        # 이미 로오버 처리했으면 변수 True 실행 못하게
                        self.future_s_roll_over_run_var = True
                        # 타이머 시작
                        self.timer1.start(Future_s_Leverage_Int * 100)
                        self.printt('future_s_roll_over_fn / option_s_delta_tuning_fn 시작 timer1 재시작')
            # -----

        # 장마감 self.MarketEndingVar == 'c' 연결선물 및 즐겨찾기 주식 시세조회
        if self.MarketEndingVar == 'c':
            # 장마감 c 이후
            self.c_to_cf_hand()

    # 지난 옵션 헤지 비율 저장하기
    def option_s_hedge_ratio_store_fn(self, option_s_hedge_ratio, myhave_sell_total_mall_basket_cnt_remove, myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int):
        # -----
        # db명
        # 파이썬 인터프리트가 현재 실행되고 있는 기계의 hostname을 스트링 형태로 return
        pc_host_name = socket.gethostname()
        pc_ip_address = socket.gethostbyname(pc_host_name)
        # print('현재 실행되고 있는 기계의 hostname / pc_ip_address')
        # print(pc_host_name)
        # print(pc_ip_address)
        db_name_option_s_hedge_ratio_data = 'option_s_hedge_ratio_' + pc_host_name
        # 딕셔너리 선언 / 저장준비
        option_s_hedge_ratio_data = {'option_s_hedge_ratio': [], 'center_option_price': [], 'fu_run_price': [], 'sell_or_buy': [], 'myhave_fu_cnt': [], 'basket_cnt': [], 'day_residue_int': [], 'signal_out': []}
        option_s_hedge_ratio_data['option_s_hedge_ratio'].append(option_s_hedge_ratio)
        option_s_hedge_ratio_data['center_option_price'].append(self.center_option_price)
        option_s_hedge_ratio_data['fu_run_price'].append(self.futrue_s_data['run_price'][0])
        if myhave_sell_total_mall_basket_cnt_remove > 0:
            sell_or_buy = 1
            myhave_total_mall_basket_cnt_remove = myhave_sell_total_mall_basket_cnt_remove
        elif myhave_buy_total_mall_basket_cnt_remove > 0:
            sell_or_buy = 2
            myhave_total_mall_basket_cnt_remove = myhave_buy_total_mall_basket_cnt_remove
        else:
            sell_or_buy = 0
            myhave_total_mall_basket_cnt_remove = 0
        option_s_hedge_ratio_data['sell_or_buy'].append(sell_or_buy)
        option_s_hedge_ratio_data['myhave_fu_cnt'].append(myhave_total_mall_basket_cnt_remove)
        option_s_hedge_ratio_data['basket_cnt'].append(basket_cnt)
        option_s_hedge_ratio_data['day_residue_int'].append(day_residue_int)
        # 저장 함수 호출
        option_s_hedge_ratio_data_store(Folder_Name_DB_Store, db_name_option_s_hedge_ratio_data, option_s_hedge_ratio_data)
        # -----

    # 지난 옵션 헤지 비율 중심가 가져오기
    def option_s_center_option_price_pickup_fn(self):
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
        if is_store_folder == False:
            os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)

        # -----
        # 지난 옵션 헤지 비율 db 호출
        # 선택db
        # db명
        choice_db_filename = 'option_s_hedge_ratio'
        choice_option_s_hedge_ratio_data_path = os.getcwd() + '/' + Folder_Name_DB_Store
        dir_list_files = os.listdir(choice_option_s_hedge_ratio_data_path)
        # option_s_hedge_ratio_data_list 리스트 생성
        option_s_hedge_ratio_data_list = []
        for f in dir_list_files:
            if f.startswith(choice_db_filename):
                option_s_hedge_ratio_data_list.append(f)
        # print(option_s_hedge_ratio_data_list)
        # ['option_s_hedge_ratio_ceo.db']
        # option_s_hedge_ratio_data_list 파일이 없으면 패스
        if len(option_s_hedge_ratio_data_list) == 0:
            return ''

        # 가장 최근일자 테이블 1건만 취하기
        for db_name in option_s_hedge_ratio_data_list:
            # 테이블명 가져오기
            con = sqlite3.connect(choice_option_s_hedge_ratio_data_path + '/' + db_name)
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            total_table_name = cursor.fetchall()
        # print(total_table_name)
        # [..., ('20240131',), ('20240201',), ('20240202',), ('20240205',)]
        if len(total_table_name) == 0:
            return ''

        # 가장 최근일자 1건만 취하기
        table_name = total_table_name[-1][0]
        self.printt('option_s_hedge_ratio 가장 최근 테이블 1건')
        self.printt('# option_s_center_option_price_pickup_fn')
        self.printt(table_name)
        df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
        # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
        # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
        # print(df_read)
        # df_read.info()
        # db닫기
        con.commit()
        con.close()
        # 가장 나중에 저장된 option_s_hedge_ratio
        last_option_s_center_option_price = df_read.iloc[-1]['center_option_price']
        # print(last_option_s_center_option_price)
        # 100 / 0
        # print(type(last_option_s_center_option_price))
        # <class 'str'>
        return last_option_s_center_option_price
        # -----

    # 지난 옵션 헤지 비율 가져오기
    def option_s_hedge_ratio_pickup_fn(self):
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
        if is_store_folder == False:
            os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)

        # -----
        # 지난 옵션 헤지 비율 db 호출
        # 선택db
        # db명
        choice_db_filename = 'option_s_hedge_ratio'
        choice_option_s_hedge_ratio_data_path = os.getcwd() + '/' + Folder_Name_DB_Store
        dir_list_files = os.listdir(choice_option_s_hedge_ratio_data_path)
        # option_s_hedge_ratio_data_list 리스트 생성
        option_s_hedge_ratio_data_list = []
        for f in dir_list_files:
            if f.startswith(choice_db_filename):
                option_s_hedge_ratio_data_list.append(f)
        # print(option_s_hedge_ratio_data_list)
        # ['option_s_hedge_ratio_ceo.db']
        # option_s_hedge_ratio_data_list 파일이 없으면 패스
        if len(option_s_hedge_ratio_data_list) == 0:
            return 100

        # 가장 최근일자 테이블 1건만 취하기
        for db_name in option_s_hedge_ratio_data_list:
            # 테이블명 가져오기
            con = sqlite3.connect(choice_option_s_hedge_ratio_data_path + '/' + db_name)
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            total_table_name = cursor.fetchall()
        # print(total_table_name)
        # [..., ('20240131',), ('20240201',), ('20240202',), ('20240205',)]
        if len(total_table_name) == 0:
            return 100

        # 가장 최근일자 1건만 취하기
        table_name = total_table_name[-1][0]
        # self.printt('option_s_hedge_ratio 가장 최근 테이블 1건')
        # self.printt('# last_option_s_hedge_ratio')
        # self.printt(table_name)
        df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
        # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
        # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
        # print(df_read)
        # df_read.info()
        # db닫기
        con.commit()
        con.close()
        # 가장 나중에 저장된 option_s_hedge_ratio
        last_option_s_hedge_ratio = df_read.iloc[-1]['option_s_hedge_ratio']
        # print(last_option_s_hedge_ratio)
        # 100 / 0
        # print(type(last_option_s_hedge_ratio))
        # <class 'numpy.int64'>
        return last_option_s_hedge_ratio
        # -----

    # 선물(진입/청산) 신호발생 db 호출
    def center_option_price_db_last_fn(self):
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
        if is_store_folder == False:
            os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)

        # -----
        # 선물(진입/청산) 신호발생 db 호출
        # 선택db
        # db명
        choice_db_filename = 'future_s_signal_out_store'
        choice_future_s_signal_out_data_path = os.getcwd() + '/' + Folder_Name_DB_Store
        dir_list_files = os.listdir(choice_future_s_signal_out_data_path)
        # choice_future_s_signal_out_data_list 리스트 생성
        choice_future_s_signal_out_data_list = []
        for f in dir_list_files:
            if f.startswith(choice_db_filename):
                choice_future_s_signal_out_data_list.append(f)
        # print(choice_future_s_signal_out_data_list)
        #     ['future_s_signal_out_store_ceo.db']
        # choice_future_s_signal_out_data_list 파일이 없으면 패스
        if len(choice_future_s_signal_out_data_list) == 0:

            # -----
            # self.printt('# 선물(진입/청산) 신호발생 db')
            # self.printt('if len(choice_future_s_signal_out_data_list) == 0:')
            # self.printt('self.center_option_price 대체')
            # self.printt(self.center_option_price)
            return self.center_option_price
            # -----

        # 가장 나중에 저장된 center_option_price
        center_option_price_lists = []
        for db_name in choice_future_s_signal_out_data_list:
            # 테이블명 가져오기
            con = sqlite3.connect(choice_future_s_signal_out_data_path + '/' + db_name)
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            total_table_name = cursor.fetchall()
            # print(total_table_name)
            # [('future_s_signal_out_data',)]
            table_name_list = []
            for i in total_table_name:
                table_name_list.append(i[0])
            # print(table_name_list)
            # ['future_s_signal_out_data']
            for table_name in table_name_list:
                df_read = pd.read_sql("SELECT * FROM " + "'" + table_name + "'", con, index_col=None)
                # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
                # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당
                # print(df_read)
                # df_read.info()
                center_option_price = df_read.iloc[-1]['center_option_price']
                # print(center_option_price)
                center_option_price_lists.append(center_option_price)
            # db닫기
            con.commit()
            con.close()
        # 가장 나중에 저장된 center_option_price
        # print(center_option_price_lists)
        # ['342.50']
        center_option_price_db_last = center_option_price_lists[-1]

        return center_option_price_db_last


    # 옵션 델타 튜닝 = > 항상 현재에 맞춰서
    def option_s_delta_tuning_fn(self, float_center_option_price, float_center_option_price_db_last, basket_cnt):
        # # 중심가 중심인덱스 / # 차월물 중심가 중심인덱스 == 0 => return  ### 20230127 중심가 중심인덱스 0일경우에 실행되는 것을 방지하기 위하여~~
        if (self.center_index == 0) or (self.center_index_45 == 0):
            return

        # -----
        # 주문 안된것 삭제, 체결 안된것 취소하기
        # state : 0(선택), 1(주문), 2(취소)
        while 0 in self.item_list_cnt_type['state']:
            # 아직 주문전이면 0(선택) 확인
            if 0 in self.item_list_cnt_type['state']:
                for i in range(len(self.item_list_cnt_type['code_no'])):
                    # 0(선택) 삭제
                    if self.item_list_cnt_type['state'][i] == 0:
                        # 리스트에서 삭제
                        del self.item_list_cnt_type['code_no'][i]
                        del self.item_list_cnt_type['cnt'][i]
                        del self.item_list_cnt_type['sell_buy_type'][i]
                        del self.item_list_cnt_type['state'][i]
                        del self.item_list_cnt_type['order_no'][i]
                        break  # 리스트 요소를 삭제하였으므로 for문 중지(다시 while문 반복하므로)
        # 1(주문) 취소처리
        if 1 in self.item_list_cnt_type['state']:
            # 최종 결과
            item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': [], 'order_no': []}
            for i in range(len(self.item_list_cnt_type['code_no'])):
                # self.item_list_cnt_type['code_no'][i][:3] == '101' 선물일때 삭제 예외
                if self.item_list_cnt_type['code_no'][i][:3] == '101':
                    continue
                # 1(주문) 취소 먼저
                if self.item_list_cnt_type['state'][i] == 1:
                    item_list_cnt_type['code_no'].append(self.item_list_cnt_type['code_no'][i])
                    # 옵션 주문처리는 1건씩만 했으므로~~~
                    item_list_cnt_type['cnt'].append(self.order_cnt_onetime)
                    item_list_cnt_type['sell_buy_type'].append(self.item_list_cnt_type['sell_buy_type'][i])
                    item_list_cnt_type['order_no'].append(self.item_list_cnt_type['order_no'][i])
                    # state : 2(취소) 변경
                    self.item_list_cnt_type['state'][i] = 2
            # 취소 던지기
            self.cancel_order(item_list_cnt_type)
        # 주문 체결 실시간에서 state : 2(취소) 삭제
        if 2 in self.item_list_cnt_type['state']:
            pass
        self.printt('self.item_list_cnt_type - 옵션 델타 튜닝 - 삭제 취소 이후')
        self.printt(self.item_list_cnt_type)
        # -----

        # 초기화
        # 최종 결과
        item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}

        # 선물 영업일 기준 잔존일
        future_s_day_residue_int = self.futrue_s_data['day_residue'][0]  # int
        # print(future_s_day_residue_int)
        # 옵션 영업일 기준 잔존일
        day_residue_int = self.output_put_option_data['day_residue'][self.center_index]     # int
        # print(day_residue_int)

        # 계좌내 선물 재고 확인
        myhave_sell_current_mall_cnt = 0
        myhave_buy_current_mall_cnt = 0
        myhave_sell_total_mall_cnt = 0
        myhave_buy_total_mall_cnt = 0
        for f in range(len(self.option_myhave['code'])):
            # 당월물
            if self.option_myhave['code'][f] == self.futrue_s_data['item_code'][0]:
                if self.option_myhave['sell_or_buy'][f] == 1:
                    myhave_sell_current_mall_cnt = myhave_sell_current_mall_cnt + self.option_myhave['myhave_cnt'][f]
                    myhave_sell_total_mall_cnt = myhave_sell_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
                elif self.option_myhave['sell_or_buy'][f] == 2:
                    myhave_buy_current_mall_cnt = myhave_buy_current_mall_cnt + self.option_myhave['myhave_cnt'][f]
                    myhave_buy_total_mall_cnt = myhave_buy_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
            # 차월물
            elif self.option_myhave['code'][f] == self.futrue_s_data_45['item_code'][0]:
                if self.option_myhave['sell_or_buy'][f] == 1:
                    myhave_sell_total_mall_cnt = myhave_sell_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
                elif self.option_myhave['sell_or_buy'][f] == 2:
                    myhave_buy_total_mall_cnt = myhave_buy_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
        # print(myhave_sell_current_mall_cnt)
        # print(myhave_buy_current_mall_cnt)
        # print(myhave_sell_total_mall_cnt)
        # print(myhave_buy_total_mall_cnt)
        # 매도재고 / 매수재고
        myhave_sell_total_mall_basket_cnt_remove = int(myhave_sell_total_mall_cnt / basket_cnt)
        myhave_buy_total_mall_basket_cnt_remove = int(myhave_buy_total_mall_cnt / basket_cnt)
        option_s_point_sum = 0

        # # -----
        # # test
        # myhave_sell_total_mall_cnt = 0
        # myhave_buy_total_mall_cnt = 9
        # myhave_sell_total_mall_basket_cnt_remove = int(myhave_sell_total_mall_cnt / basket_cnt)
        # myhave_buy_total_mall_basket_cnt_remove = int(myhave_buy_total_mall_cnt / basket_cnt)
        # float_center_option_price = 352.5
        # # -----

        # -----
        # option_s_hedge_ratio 초기화 [0%/100%, 50%/100%, 66%/100%]
        # 선물 재고가 없을경우에는 옵션 헤지 비율 0
        option_s_hedge_ratio = 0
        # 선물 매도재고 => 풋청산(매수) 후 풋매도
        if myhave_sell_total_mall_basket_cnt_remove > 0:
            self.printt('선물 매도재고 있음')
            self.printt(myhave_sell_total_mall_cnt)
            # 선물 매도재고(3)
            if myhave_sell_total_mall_basket_cnt_remove >= 3:
                # 장마감 self.MarketEndingVar == '2'
                if self.MarketEndingVar == '2':
                    option_s_hedge_ratio = 100
                elif float_center_option_price >= float_center_option_price_db_last:
                    option_s_hedge_ratio = 100
                    # print(option_s_hedge_ratio)
                elif float_center_option_price < float_center_option_price_db_last:
                    option_s_hedge_ratio = 66
                    # print(option_s_hedge_ratio)
            # 선물 매도재고(2)
            elif myhave_sell_total_mall_basket_cnt_remove >= 2:
                # 장마감 self.MarketEndingVar == '2'
                if self.MarketEndingVar == '2':
                    option_s_hedge_ratio = 100
                elif float_center_option_price >= float_center_option_price_db_last:
                    option_s_hedge_ratio = 100
                    # print(option_s_hedge_ratio)
                elif float_center_option_price < float_center_option_price_db_last:
                    option_s_hedge_ratio = 50
                    # print(option_s_hedge_ratio)
            # 선물 매도재고(1)
            elif myhave_sell_total_mall_basket_cnt_remove >= 1:
                # 장마감 self.MarketEndingVar == '2'
                if self.MarketEndingVar == '2':
                    option_s_hedge_ratio = 100
                elif float_center_option_price >= float_center_option_price_db_last:
                    option_s_hedge_ratio = 100
                    # print(option_s_hedge_ratio)
                elif float_center_option_price < float_center_option_price_db_last:
                    option_s_hedge_ratio = 0
                    # print(option_s_hedge_ratio)

            # 옵션 종목검색()
            put_or_call = 'put'
            # 장마감 self.MarketEndingVar == '2'
            # 장마감 2 이후
            if (day_residue_int == 1) and (self.MarketEndingVar == '2'):
                month_mall_type = 'center_index_45'
                # center_index / center_index_45
            else:
                month_mall_type = 'center_index'
                # center_index / center_index_45
            item_list_cnt_type = self.option_s_sell_items_search(myhave_sell_total_mall_cnt, option_s_hedge_ratio, put_or_call, month_mall_type)
            # print(item_list_cnt_type)
            # item_list_cnt_type = {'code_no': ['301V2337'], 'cnt': [3], 'sell_buy_type': [2]}      # option_s_sell_items_search 결과값

            # # -----
            # # 텍스트 저장은 종목이 있을경우에만
            # if len(item_list_cnt_type['code_no']) > 0:
            #     item_list_cnt_for_store = {'code_no': [], 'cnt': []}
            #     for s in range(len(item_list_cnt_type['code_no'])):
            #         item_list_cnt_for_store['code_no'].append(item_list_cnt_type['code_no'][s])
            #         item_list_cnt_for_store['cnt'].append(item_list_cnt_type['cnt'][s])
            #     # 종목코드와 수량(텍스트에 저장하기)
            #     self.today_put_order_list_text_store(item_list_cnt_for_store)
            # # -----

        # 선물 매수재고 => 콜청산(매수) 후 콜매도
        elif myhave_buy_total_mall_basket_cnt_remove > 0:
            self.printt('선물 매수재고 있음')
            self.printt(myhave_buy_total_mall_cnt)
            # 선물 매수재고(3)
            if myhave_buy_total_mall_basket_cnt_remove >= 3:
                # 장마감 self.MarketEndingVar == '2'
                if self.MarketEndingVar == '2':
                    option_s_hedge_ratio = 100
                elif float_center_option_price <= float_center_option_price_db_last:
                    option_s_hedge_ratio = 100
                    # print(option_s_hedge_ratio)
                elif float_center_option_price > float_center_option_price_db_last:
                    option_s_hedge_ratio = 66
                    # print(option_s_hedge_ratio)
            # 선물 매수재고(2)
            elif myhave_buy_total_mall_basket_cnt_remove >= 2:
                # 장마감 self.MarketEndingVar == '2'
                if self.MarketEndingVar == '2':
                    option_s_hedge_ratio = 100
                elif float_center_option_price <= float_center_option_price_db_last:
                    option_s_hedge_ratio = 100
                    # print(option_s_hedge_ratio)
                elif float_center_option_price > float_center_option_price_db_last:
                    option_s_hedge_ratio = 50
                    # print(option_s_hedge_ratio)
            # 선물 매수재고(1)
            elif myhave_buy_total_mall_basket_cnt_remove >= 1:
                # 장마감 self.MarketEndingVar == '2'
                if self.MarketEndingVar == '2':
                    option_s_hedge_ratio = 100
                elif float_center_option_price <= float_center_option_price_db_last:
                    option_s_hedge_ratio = 100
                    # print(option_s_hedge_ratio)
                elif float_center_option_price > float_center_option_price_db_last:
                    option_s_hedge_ratio = 0
                    # print(option_s_hedge_ratio)
            # 옵션 종목검색()
            put_or_call = 'call'
            # 장마감 self.MarketEndingVar == '2'
            # 장마감 2 이후
            if (day_residue_int == 1) and (self.MarketEndingVar == '2'):
                month_mall_type = 'center_index_45'
                # center_index / center_index_45
            else:
                month_mall_type = 'center_index'
                # center_index / center_index_45
            item_list_cnt_type = self.option_s_sell_items_search(myhave_buy_total_mall_cnt, option_s_hedge_ratio, put_or_call, month_mall_type)
            # print(item_list_cnt_type)
            # item_list_cnt_type = {'code_no': ['301V2337'], 'cnt': [3], 'sell_buy_type': [2]}      # option_s_sell_items_search 결과값

            # # 텍스트 저장은 종목이 있을경우에만
            # if len(item_list_cnt_type['code_no']) > 0:
            #     item_list_cnt_for_store = {'code_no': [], 'cnt': []}
            #     for s in range(len(item_list_cnt_type['code_no'])):
            #         item_list_cnt_for_store['code_no'].append(item_list_cnt_type['code_no'][s])
            #         item_list_cnt_for_store['cnt'].append(item_list_cnt_type['cnt'][s])
            #     # 종목코드와 수량(텍스트에 저장하기)
            #     self.today_call_order_list_text_store(item_list_cnt_for_store)

        else:
            # -----
            # 만일 선물 재고 0 옵션 재고가 있을 때(clear)
            for p in range(len(self.option_myhave['code'])):
                # 선물재고는 pass
                if self.option_myhave['code'][p][:3] == '101':
                    pass
                # 재고가 혹시 매도
                elif self.option_myhave['sell_or_buy'][p] == 1:
                    item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    item_list_cnt_type['sell_buy_type'].append(2)
                # 재고가 행여나 매수
                elif self.option_myhave['sell_or_buy'][p] == 2:
                    item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    item_list_cnt_type['sell_buy_type'].append(1)
            # -----
        # print(item_list_cnt_type)

        # 옵션 헤지 비율 저장하기
        self.option_s_hedge_ratio_store_fn(option_s_hedge_ratio, myhave_sell_total_mall_basket_cnt_remove, myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int)

        # -----
        # 매도재고 / 매수재고
        # myhave_sell_total_mall_basket_cnt_remove = int(myhave_sell_total_mall_cnt / basket_cnt)
        # myhave_buy_total_mall_basket_cnt_remove = int(myhave_buy_total_mall_cnt / basket_cnt)
        # 옵션 모두 청산시에는 체크 안함(종목검색에서만 option_s_sell_order_deposit_money를 계산하기 때문에)
        if (myhave_sell_total_mall_basket_cnt_remove >= 1) or (myhave_buy_total_mall_basket_cnt_remove >= 1):
            self.printt('옵션 델타 튜닝 결색결과 리스트')
            self.printt(item_list_cnt_type)
            for r in range(len(item_list_cnt_type['code_no'])):
                if item_list_cnt_type['sell_buy_type'][r] == 1:
                    # 이번 변경시 옵션매도 주문 가능 건수
                    # print(self.option_order_able_money)
                    # print(self.option_s_sell_order_deposit_money)
                    now_option_s_sell_order_able_cnt = math.floor(self.option_order_able_money / self.option_s_sell_order_deposit_money)
                    if item_list_cnt_type['cnt'][r] > now_option_s_sell_order_able_cnt:
                        item_list_cnt_type['cnt'][r] = now_option_s_sell_order_able_cnt
            self.printt('옵션 매도 최대금액 감안 리스트')
            self.printt(item_list_cnt_type)
        # -----

        # 검색된 종목코드 여부
        item_list_cnt = len(item_list_cnt_type['code_no'])
        if item_list_cnt > 0:
            for i in range(len(item_list_cnt_type['code_no'])):
                self.item_list_cnt_type['code_no'].append(item_list_cnt_type['code_no'][i])
                self.item_list_cnt_type['cnt'].append(item_list_cnt_type['cnt'][i])
                self.item_list_cnt_type['sell_buy_type'].append(item_list_cnt_type['sell_buy_type'][i])
                self.item_list_cnt_type['state'].append(0)
                self.item_list_cnt_type['order_no'].append(0)

    # 중심가 변경시
    def option_s_center_index_change_ready(self):
        # -----
        # 중심가 변경시 처리항목 정리[20240122 - fu2060_이벤트처리 docx파일 참조]
        # 예탁금및증거금조회 - 이벤트 슬롯
        self.mymoney_option_rq()
        # 계좌평가잔고내역요청[stock]
        self.stock_have_data_rq()
        # 선옵계좌별주문가능수량요청
        item_code = self.futrue_s_data['item_code'][0]
        sell_or_buy_type = '1'  # 매도 매수 타입 # "매매구분"(1:매도, 2:매수)
        price_type = '1'  # 주문유형 = 1:지정가, 3:시장가
        item_order_price_six_digit = int(self.futrue_s_data['run_price'][0] * 1000)
        # print(item_order_price_six_digit)
        item_order_price_five_digit_str = str(item_order_price_six_digit)
        # print(item_order_price_five_digit_str)
        self.future_s_option_s_order_able_cnt_rq(item_code, sell_or_buy_type, price_type,
                                                 item_order_price_five_digit_str)
        # 서버구분(모의서버 : '1' /실서버 : '')
        if self.get_server_gubun() == '':
            # 옵션매도주문증거금 요청
            self.option_s_sell_deposit_money_data_rq()
        # -----

        # -----
        # 실시간 관리중인 콜 풋 데이터
        self.printt('# 실시간 관리중인 콜 풋 데이터')
        self.printt(self.output_call_option_data)
        self.printt(self.output_put_option_data)
        # 차월물
        self.printt(self.output_call_option_data_45)
        self.printt(self.output_put_option_data_45)

        # 실시간 관리중인 선물전체시세 데이터
        self.printt('# 실시간 관리중인 선물전체시세 데이터')
        self.printt(self.futrue_s_data)
        # 차월물
        self.printt(self.futrue_s_data_45)
        # -----

        # 선물 바스켓 가져오기
        basket_cnt = self.future_s_basket_cnt_text_read()   #int
        # print(basket_cnt)

        # 옵션 영업일 기준 잔존일
        day_residue_int = self.output_put_option_data['day_residue'][self.center_index]     # int
        # print(day_residue_int)

        # 계좌내 선물 재고 확인
        myhave_sell_current_mall_cnt = 0
        myhave_buy_current_mall_cnt = 0
        myhave_sell_total_mall_cnt = 0
        myhave_buy_total_mall_cnt = 0
        for f in range(len(self.option_myhave['code'])):
            # 당월물
            if self.option_myhave['code'][f] == self.futrue_s_data['item_code'][0]:
                if self.option_myhave['sell_or_buy'][f] == 1:
                    myhave_sell_current_mall_cnt = myhave_sell_current_mall_cnt + self.option_myhave['myhave_cnt'][f]
                    myhave_sell_total_mall_cnt = myhave_sell_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
                elif self.option_myhave['sell_or_buy'][f] == 2:
                    myhave_buy_current_mall_cnt = myhave_buy_current_mall_cnt + self.option_myhave['myhave_cnt'][f]
                    myhave_buy_total_mall_cnt = myhave_buy_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
            # 차월물
            elif self.option_myhave['code'][f] == self.futrue_s_data_45['item_code'][0]:
                if self.option_myhave['sell_or_buy'][f] == 1:
                    myhave_sell_total_mall_cnt = myhave_sell_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
                elif self.option_myhave['sell_or_buy'][f] == 2:
                    myhave_buy_total_mall_cnt = myhave_buy_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
        # print(myhave_sell_current_mall_cnt)
        # print(myhave_buy_current_mall_cnt)
        # print(myhave_sell_total_mall_cnt)
        # print(myhave_buy_total_mall_cnt)
        # 매도재고 / 매수재고
        myhave_sell_total_mall_basket_cnt_remove = int(myhave_sell_total_mall_cnt / basket_cnt)
        myhave_buy_total_mall_basket_cnt_remove = int(myhave_buy_total_mall_cnt / basket_cnt)

        # -----
        # 현재의 선물 매도/매수 옵션 매도/매수 상황에 따른 자산가치 정리해서 db저장
        # db명
        # 파이썬 인터프리트가 현재 실행되고 있는 기계의 hostname을 스트링 형태로 return
        pc_host_name = socket.gethostname()
        pc_ip_address = socket.gethostbyname(pc_host_name)
        # print('현재 실행되고 있는 기계의 hostname / pc_ip_address')
        # print(pc_host_name)
        # print(pc_ip_address)
        db_name_center_option_s_change_data = 'center_option_s_change_state_' + pc_host_name
        # 딕셔너리 선언 / 저장준비
        center_option_s_change_data = {'center_option_price': [], 'fu_run_price': [], 'sell_or_buy': [], 'myhave_fu_cnt': [], 'basket_cnt': [], 'option_s_point_sum': [], 'option_s_point_in': [], 'option_s_point_myhave': [], 'day_residue_int': [], 'my_total_money': []}
        center_option_s_change_data['center_option_price'].append(self.center_option_price)
        center_option_s_change_data['fu_run_price'].append(self.futrue_s_data['run_price'][0])
        if myhave_sell_total_mall_basket_cnt_remove > 0:
            sell_or_buy = 1
            myhave_total_mall_basket_cnt_remove = myhave_sell_total_mall_basket_cnt_remove
        elif myhave_buy_total_mall_basket_cnt_remove > 0:
            sell_or_buy = 2
            myhave_total_mall_basket_cnt_remove = myhave_buy_total_mall_basket_cnt_remove
        else:
            sell_or_buy = 0
            myhave_total_mall_basket_cnt_remove = 0
        center_option_s_change_data['sell_or_buy'].append(sell_or_buy)
        center_option_s_change_data['myhave_fu_cnt'].append(myhave_total_mall_basket_cnt_remove)
        center_option_s_change_data['basket_cnt'].append(basket_cnt)

        # -----
        # 호환성 유지(델타 0 맞춤 업글시)
        center_option_s_change_data['option_s_point_sum'].append('')
        center_option_s_change_data['option_s_point_in'].append('')
        center_option_s_change_data['option_s_point_myhave'].append('')
        # -----

        center_option_s_change_data['day_residue_int'].append(day_residue_int)
        # 선물옵션 순자산금액 + stock 추정예탁자산
        option_have_money_plus_estimated_deposit = self.option_have_money + self.estimated_deposit
        center_option_s_change_data['my_total_money'].append(option_have_money_plus_estimated_deposit)
        # 저장 함수 호출
        center_option_s_change_data_store(Folder_Name_DB_Store, db_name_center_option_s_change_data, center_option_s_change_data)
        # -----

    # 선물(진입/청산) 준비
    def future_s_market_ready(self, last_option_s_hedge_ratio, basket_cnt):
        # 당일날 선물 주문 있었으면 return
        # 당일 매도 종목
        # 당월물
        if self.futrue_s_data['item_code'][0] in self.selled_today_items:
            return
        # 차월물
        if self.futrue_s_data_45['item_code'][0] in self.selled_today_items:
            return
        # 당일 매수 종목
        # 당월물
        if self.futrue_s_data['item_code'][0] in self.buyed_today_items:
            return
        # 차월물
        if self.futrue_s_data_45['item_code'][0] in self.buyed_today_items:
            return
        # 연결선물가상매매
        if Chain_Future_s_Item_Code[0] in self.selled_today_items:
            return
        if Chain_Future_s_Item_Code[0] in self.buyed_today_items:
            return

        # -----
        # 초단위 주문변수 체크(전송목록)
        # 당월물
        if self.futrue_s_data['item_code'][0] in self.item_list_cnt_type['code_no']:
            return
        # 차월물
        if self.futrue_s_data_45['item_code'][0] in self.item_list_cnt_type['code_no']:
            return
        # 연결선물가상매매
        if Chain_Future_s_Item_Code[0] in self.item_list_cnt_type['code_no']:
            return
        # -----

        # 주문변수 초기화
        item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}

        # 선물 영업일 기준 잔존일
        future_s_day_residue_int = self.futrue_s_data['day_residue'][0]  # int
        # print(future_s_day_residue_int)
        # 옵션 영업일 기준 잔존일
        day_residue_int = self.output_put_option_data['day_residue'][self.center_index]     # int
        # print(day_residue_int)

        # 계좌내 선물 재고 확인
        myhave_sell_current_mall_cnt = 0
        myhave_buy_current_mall_cnt = 0
        myhave_sell_total_mall_cnt = 0
        myhave_buy_total_mall_cnt = 0
        for f in range(len(self.option_myhave['code'])):
            # 당월물
            if self.option_myhave['code'][f] == self.futrue_s_data['item_code'][0]:
                if self.option_myhave['sell_or_buy'][f] == 1:
                    myhave_sell_current_mall_cnt = myhave_sell_current_mall_cnt + self.option_myhave['myhave_cnt'][f]
                    myhave_sell_total_mall_cnt = myhave_sell_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
                elif self.option_myhave['sell_or_buy'][f] == 2:
                    myhave_buy_current_mall_cnt = myhave_buy_current_mall_cnt + self.option_myhave['myhave_cnt'][f]
                    myhave_buy_total_mall_cnt = myhave_buy_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
            # 차월물
            elif self.option_myhave['code'][f] == self.futrue_s_data_45['item_code'][0]:
                if self.option_myhave['sell_or_buy'][f] == 1:
                    myhave_sell_total_mall_cnt = myhave_sell_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
                elif self.option_myhave['sell_or_buy'][f] == 2:
                    myhave_buy_total_mall_cnt = myhave_buy_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
        # print(myhave_sell_current_mall_cnt)
        # print(myhave_buy_current_mall_cnt)
        # print(myhave_sell_total_mall_cnt)
        # print(myhave_buy_total_mall_cnt)
        # 매도재고 / 매수재고
        myhave_sell_total_mall_basket_cnt_remove = int(myhave_sell_total_mall_cnt / basket_cnt)
        myhave_buy_total_mall_basket_cnt_remove = int(myhave_buy_total_mall_cnt / basket_cnt)
        # ai
        # 월봉
        # 3차원 기울기 체크
        # future_s_month_poly_gradient = 'sell_or_buy_time'
        # if self.stock_trend_line_of_ai_month != None:
        #     for i in range(len(self.stock_trend_line_of_ai_month['stock_no'])):
        #         # 연결선물
        #         if Chain_Future_s_Item_Code[0] == self.stock_trend_line_of_ai_month['stock_no'][i]:
        #             # 월봉 3차원 기울기 하향중
        #             if ((self.stock_trend_line_of_ai_month['poly_h_gradient'][i] < 0) and (
        #                     self.stock_trend_line_of_ai_month['poly_l_gradient'][i] < 0)):
        #                 future_s_month_poly_gradient = 'sell_time'
        #             # 월봉 3차원 기울기 상향중
        #             elif ((self.stock_trend_line_of_ai_month['poly_h_gradient'][i] > 0) and (
        #                     self.stock_trend_line_of_ai_month['poly_l_gradient'][i] > 0)):
        #                 future_s_month_poly_gradient = 'buy_time'
        # print(future_s_month_poly_gradient)
        # 일봉
        day_poly_max_price = 9999999
        day_poly_min_price = 0
        for i in range(len(self.stock_trend_line_of_ai_day['stock_no'])):
            # 연결선물
            if Chain_Future_s_Item_Code[0] == self.stock_trend_line_of_ai_day['stock_no'][i]:
                day_poly_max_price = self.stock_trend_line_of_ai_day['poly_sell_max_price'][i]
                day_poly_min_price = self.stock_trend_line_of_ai_day['poly_buy_min_price'][i]
        # print(day_poly_max_price)
        # print(day_poly_min_price)

        # 계좌내 선물 재고 확인
        # 계좌내 당월물 재고있음
        if self.futrue_s_data['item_code'][0] in self.option_myhave['code']:
            # 계좌내 당월물 재고있음 day_poly_max_price / day_poly_min_price 신호발생
            if self.futrue_s_data['run_price'][0] > day_poly_max_price:
                self.printt('당월물 재고있음 선물매도(1) 신호발생')
                # 선물(진입/청산) 신호발생시 db 저장
                signal_out = 1
                self.printt('# 선물(진입/청산) 신호발생시 db 저장')
                self.future_s_signal_out_store_fn(myhave_sell_total_mall_basket_cnt_remove,
                                             myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int, signal_out)
                # 롤오버 감안 미리 차월물 진입 여부
                # 재고수량과 비교하여 잔존일이 2일 이상 남았으면 당월물 그렇지 않으면 차월물
                if myhave_sell_current_mall_cnt > 0:
                    self.printt('매도재고 있음')
                    sell_roll_over_check_cnt = int(myhave_sell_current_mall_cnt / basket_cnt)
                    if future_s_day_residue_int > (sell_roll_over_check_cnt + 2):
                        self.printt('당월물 진입')
                        # 선물재고 건수 및 옵션재고 확인
                        if myhave_sell_total_mall_basket_cnt_remove >= 3 or last_option_s_hedge_ratio == 100:
                            # 매도재고 : 매도신호 => 선물매도 건수가 바스켓 기준으로 3이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                            self.printt('(>= 3)선물매도 건수가 바스켓 기준으로 3이상이면 거래없음')
                            self.printt('또는 지난헤지비율 100이면 거래없음')
                            self.printt(myhave_sell_total_mall_basket_cnt_remove)
                            self.printt(last_option_s_hedge_ratio)

                            # 연결선물가상매매
                            SellBuyType = '매도'
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            time_msg = ' 연결선물가상매매 : ' + text_time + ' 선물재고(' + str(
                                myhave_sell_total_mall_basket_cnt_remove) + \
                                       ')' + ' 지난헤지비율(' + str(last_option_s_hedge_ratio) + ')'
                            # 텍스트 저장 호출
                            self.printt_selled(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                            return
                        elif myhave_sell_total_mall_basket_cnt_remove == 2:
                            # # 옵션 종목검색(풋매도)
                            # put_or_call = 'put'
                            # if day_residue_int > 2:
                            #     month_mall_type = 'center_index'
                            #     # center_index / center_index_45
                            # else:
                            #     month_mall_type = 'center_index_45'
                            #     # center_index / center_index_45
                            #
                            # item_list_cnt_type = self.option_s_sell_items_search(myhave_sell_total_mall_cnt, put_or_call,
                            #                                                   month_mall_type)
                            # # print(item_list_cnt_type)
                            # # item_list_cnt_type = {'code_no': ['301V2337'], 'cnt': [3], 'sell_buy_type': [2]}      # option_s_sell_items_search 결과값
                            # self.printt('(== 2)옵션 종목검색(풋매도)')
                            # self.printt(item_list_cnt_type)
                            #
                            # # -----
                            # # 텍스트 저장은 종목이 있을경우에만
                            # if len(item_list_cnt_type['code_no']) > 0:
                            #     item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            #     for i in range(len(item_list_cnt_type['code_no'])):
                            #         item_list_cnt_for_store['code_no'].append(item_list_cnt_type['code_no'][i])
                            #         item_list_cnt_for_store['cnt'].append(item_list_cnt_type['cnt'][i])
                            #     # 종목코드와 수량(텍스트에 저장하기)
                            #     self.today_put_order_list_text_store(item_list_cnt_for_store)
                            # # -----

                            # 일반 진입
                            self.printt('(== 2)옵션 진입없음, 일반 진입')
                            pass

                        elif myhave_sell_total_mall_basket_cnt_remove == 1:
                            # 일반 진입
                            self.printt('(== 1)옵션 진입없음, 일반 진입')
                            pass

                        # 선물매도
                        item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                        item_list_cnt_type['cnt'].append(basket_cnt)
                        item_list_cnt_type['sell_buy_type'].append(1)
                        # print(item_list_cnt_type)

                    elif future_s_day_residue_int <= (sell_roll_over_check_cnt + 2):
                        self.printt('차월물 진입')
                        # 선물재고 건수 및 옵션재고 확인
                        if myhave_sell_total_mall_basket_cnt_remove >= 3 or last_option_s_hedge_ratio == 100:
                            # 매도재고 : 매도신호 => 선물매도 건수가 바스켓 기준으로 3이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                            self.printt('(>= 3)선물매도 건수가 바스켓 기준으로 3이상이면 거래없음')
                            self.printt('또는 지난헤지비율 100이면 거래없음')
                            self.printt(myhave_sell_total_mall_basket_cnt_remove)
                            self.printt(last_option_s_hedge_ratio)

                            # 연결선물가상매매
                            SellBuyType = '매도'
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            time_msg = ' 연결선물가상매매 : ' + text_time + ' 선물재고(' + str(
                                myhave_sell_total_mall_basket_cnt_remove) + \
                                       ')' + ' 지난헤지비율(' + str(last_option_s_hedge_ratio) + ')'
                            # 텍스트 저장 호출
                            self.printt_selled(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                            return
                        elif myhave_sell_total_mall_basket_cnt_remove == 2:
                            # # 옵션 종목검색(풋매도)
                            # put_or_call = 'put'
                            # if day_residue_int > 2:
                            #     month_mall_type = 'center_index'
                            #     # center_index / center_index_45
                            # else:
                            #     month_mall_type = 'center_index_45'
                            #     # center_index / center_index_45
                            #
                            # item_list_cnt_type = self.option_s_sell_items_search(myhave_sell_total_mall_cnt, put_or_call,
                            #                                                   month_mall_type)
                            # # print(item_list_cnt_type)
                            # # item_list_cnt_type = {'code_no': ['301V2337'], 'cnt': [3], 'sell_buy_type': [2]}      # option_s_sell_items_search 결과값
                            # self.printt('(== 2)옵션 종목검색(풋매도)')
                            # self.printt(item_list_cnt_type)
                            #
                            # # -----
                            # # 텍스트 저장은 종목이 있을경우에만
                            # if len(item_list_cnt_type['code_no']) > 0:
                            #     item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            #     for i in range(len(item_list_cnt_type['code_no'])):
                            #         item_list_cnt_for_store['code_no'].append(item_list_cnt_type['code_no'][i])
                            #         item_list_cnt_for_store['cnt'].append(item_list_cnt_type['cnt'][i])
                            #     # 종목코드와 수량(텍스트에 저장하기)
                            #     self.today_put_order_list_text_store(item_list_cnt_for_store)
                            # # -----

                            # 일반 진입
                            self.printt('(== 2)옵션 진입없음, 일반 진입')
                            pass

                        elif myhave_sell_total_mall_basket_cnt_remove == 1:
                            # 일반 진입
                            self.printt('(== 1)옵션 진입없음, 일반 진입')
                            pass

                        # 선물매도
                        item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                        item_list_cnt_type['cnt'].append(basket_cnt)
                        item_list_cnt_type['sell_buy_type'].append(1)
                        # print(item_list_cnt_type)

                elif myhave_buy_current_mall_cnt > 0:
                    self.printt('매수재고 있음')
                    self.printt('당월물 청산')

                    # # -----
                    # # 만일 재고가 2이하 인데 옵션 재고가 있을 때
                    # for p in range(len(self.option_myhave['code'])):
                    #     # 선물재고는 pass
                    #     if self.option_myhave['code'][p][:3] == '101':
                    #         pass
                    #     # 재고가 혹시 매도
                    #     elif self.option_myhave['sell_or_buy'][p] == 1:
                    #         item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    #         item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    #         item_list_cnt_type['sell_buy_type'].append(2)
                    #     # 재고가 행여나 매수
                    #     elif self.option_myhave['sell_or_buy'][p] == 2:
                    #         item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    #         item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    #         item_list_cnt_type['sell_buy_type'].append(1)
                    # # -----

                    # 선물매도
                    item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
                    # print(item_list_cnt_type)
            elif self.futrue_s_data['run_price'][0] < day_poly_min_price:
                self.printt('당월물 재고있음 선물매수(2) 신호발생')
                # 선물(진입/청산) 신호발생시 db 저장
                signal_out = 2
                self.printt('# 선물(진입/청산) 신호발생시 db 저장')
                self.future_s_signal_out_store_fn(myhave_sell_total_mall_basket_cnt_remove,
                                                  myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int,
                                                  signal_out)
                # 롤오버 감안 미리 차월물 진입 여부
                # 재고수량과 비교하여 잔존일이 2일 이상 남았으면 당월물 그렇지 않으면 차월물
                if myhave_sell_current_mall_cnt > 0:
                    self.printt('매도재고 있음')
                    self.printt('당월물 청산')

                    # # -----
                    # # 만일 재고가 2이하 인데 옵션 재고가 있을 때
                    # for p in range(len(self.option_myhave['code'])):
                    #     # 선물재고는 pass
                    #     if self.option_myhave['code'][p][:3] == '101':
                    #         pass
                    #     # 재고가 혹시 매도
                    #     elif self.option_myhave['sell_or_buy'][p] == 1:
                    #         item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    #         item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    #         item_list_cnt_type['sell_buy_type'].append(2)
                    #     # 재고가 행여나 매수
                    #     elif self.option_myhave['sell_or_buy'][p] == 2:
                    #         item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    #         item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    #         item_list_cnt_type['sell_buy_type'].append(1)
                    # # -----

                    # 선물매수
                    item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(2)
                    # print(item_list_cnt_type)

                elif myhave_buy_current_mall_cnt > 0:
                    self.printt('매수재고 있음')
                    buy_roll_over_check_cnt = int(myhave_buy_current_mall_cnt / basket_cnt)
                    if future_s_day_residue_int > (buy_roll_over_check_cnt + 2):
                        self.printt('당월물 진입')
                        # 선물재고 건수 및 옵션재고 확인
                        if myhave_buy_total_mall_basket_cnt_remove >= 3 or last_option_s_hedge_ratio == 100:
                            # 매수재고 : 매수신호 => 선물매수 건수가 바스켓 기준으로 3이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                            self.printt('(>= 3)선물매수 건수가 바스켓 기준으로 3이상이면 거래없음')
                            self.printt('또는 지난헤지비율 100이면 거래없음')
                            self.printt(myhave_sell_total_mall_basket_cnt_remove)
                            self.printt(last_option_s_hedge_ratio)

                            # 연결선물가상매매
                            SellBuyType = '매수'
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            time_msg = ' 연결선물가상매매 : ' + text_time + ' 선물재고(' + str(
                                myhave_sell_total_mall_basket_cnt_remove) + \
                                       ')' + ' 지난헤지비율(' + str(last_option_s_hedge_ratio) + ')'
                            # 텍스트 저장 호출
                            self.printt_buyed(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                            return
                        elif myhave_buy_total_mall_basket_cnt_remove == 2:
                            # # 옵션 종목검색(콜매도)
                            # put_or_call = 'call'
                            # if day_residue_int > 2:
                            #     month_mall_type = 'center_index'
                            #     # center_index / center_index_45
                            # else:
                            #     month_mall_type = 'center_index_45'
                            #     # center_index / center_index_45
                            #
                            # item_list_cnt_type = self.option_s_sell_items_search(myhave_buy_total_mall_cnt, put_or_call,
                            #                                               month_mall_type)
                            # # print(item_list_cnt_type)
                            # # item_list_cnt_type = {'code_no': ['301V2337'], 'cnt': [3], 'sell_buy_type': [2]}      # option_s_sell_items_search 결과값
                            # self.printt('(== 2)옵션 종목검색(콜매도)')
                            # self.printt(item_list_cnt_type)
                            #
                            # # -----
                            # # 텍스트 저장은 종목이 있을경우에만
                            # if len(item_list_cnt_type['code_no']) > 0:
                            #     item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            #     for i in range(len(item_list_cnt_type['code_no'])):
                            #         item_list_cnt_for_store['code_no'].append(item_list_cnt_type['code_no'][i])
                            #         item_list_cnt_for_store['cnt'].append(item_list_cnt_type['cnt'][i])
                            #     # 종목코드와 수량(텍스트에 저장하기)
                            #     self.today_call_order_list_text_store(item_list_cnt_for_store)
                            # # -----

                            # 일반 진입
                            self.printt('(== 2)옵션 진입없음, 일반 진입')
                            pass

                        elif myhave_buy_total_mall_basket_cnt_remove == 1:
                            # 일반 진입
                            self.printt('(== 1)옵션 진입없음, 일반 진입')
                            pass

                        # 선물매수
                        item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                        item_list_cnt_type['cnt'].append(basket_cnt)
                        item_list_cnt_type['sell_buy_type'].append(2)
                        # print(item_list_cnt_type)
                    elif future_s_day_residue_int <= (buy_roll_over_check_cnt + 2):
                        self.printt('차월물 진입')

                        # 선물재고 건수 및 옵션재고 확인
                        if myhave_buy_total_mall_basket_cnt_remove >= 3 or last_option_s_hedge_ratio == 100:
                            # 매수재고 : 매수신호 => 선물매수 건수가 바스켓 기준으로 3이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                            self.printt('(>= 3)선물매수 건수가 바스켓 기준으로 3이상이면 거래없음')
                            self.printt('또는 지난헤지비율 100이면 거래없음')
                            self.printt(myhave_sell_total_mall_basket_cnt_remove)
                            self.printt(last_option_s_hedge_ratio)

                            # 연결선물가상매매
                            SellBuyType = '매수'
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            time_msg = ' 연결선물가상매매 : ' + text_time + ' 선물재고(' + str(
                                myhave_sell_total_mall_basket_cnt_remove) + \
                                       ')' + ' 지난헤지비율(' + str(last_option_s_hedge_ratio) + ')'
                            # 텍스트 저장 호출
                            self.printt_buyed(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                            return
                        elif myhave_buy_total_mall_basket_cnt_remove == 2:
                            # # 옵션 종목검색(콜매도)
                            # put_or_call = 'call'
                            # if day_residue_int > 2:
                            #     month_mall_type = 'center_index'
                            #     # center_index / center_index_45
                            # else:
                            #     month_mall_type = 'center_index_45'
                            #     # center_index / center_index_45
                            #
                            # item_list_cnt_type = self.option_s_sell_items_search(myhave_buy_total_mall_cnt, put_or_call,
                            #                                               month_mall_type)
                            # # print(item_list_cnt_type)
                            # # item_list_cnt_type = {'code_no': ['301V2337'], 'cnt': [3], 'sell_buy_type': [2]}      # option_s_sell_items_search 결과값
                            # self.printt('(== 2)옵션 종목검색(콜매도)')
                            # self.printt(item_list_cnt_type)
                            #
                            # # -----
                            # # 텍스트 저장은 종목이 있을경우에만
                            # if len(item_list_cnt_type['code_no']) > 0:
                            #     item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            #     for i in range(len(item_list_cnt_type['code_no'])):
                            #         item_list_cnt_for_store['code_no'].append(item_list_cnt_type['code_no'][i])
                            #         item_list_cnt_for_store['cnt'].append(item_list_cnt_type['cnt'][i])
                            #     # 종목코드와 수량(텍스트에 저장하기)
                            #     self.today_call_order_list_text_store(item_list_cnt_for_store)
                            # # -----

                            # 일반 진입
                            self.printt('(== 2)옵션 진입없음, 일반 진입')
                            pass

                        elif myhave_buy_total_mall_basket_cnt_remove == 1:
                            # 일반 진입
                            self.printt('(== 1)옵션 진입없음, 일반 진입')
                            pass

                        # 선물매수
                        item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                        item_list_cnt_type['cnt'].append(basket_cnt)
                        item_list_cnt_type['sell_buy_type'].append(2)
                        # print(item_list_cnt_type)

        # 계좌내 차월물만 재고있음
        elif self.futrue_s_data_45['item_code'][0] in self.option_myhave['code']:
            # 계좌내 차월물만 재고있음 day_poly_max_price / day_poly_min_price 신호발생
            # 신호확인은 당월물로
            if self.futrue_s_data['run_price'][0] > day_poly_max_price:
                self.printt('차월물만 재고있음 선물매도(1) 신호발생')
                # 선물(진입/청산) 신호발생시 db 저장
                signal_out = 1
                self.printt('# 선물(진입/청산) 신호발생시 db 저장')
                self.future_s_signal_out_store_fn(myhave_sell_total_mall_basket_cnt_remove,
                                                  myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int,
                                                  signal_out)
                # 재고수량 (매도/ 매수) 비교
                if myhave_sell_total_mall_cnt > 0:
                    self.printt('매도재고 있음')
                    self.printt('차월물만 진입')

                    # 선물재고 건수 및 옵션재고 확인
                    if myhave_sell_total_mall_basket_cnt_remove >= 3 or last_option_s_hedge_ratio == 100:
                        # 매도재고 : 매도신호 => 선물매도 건수가 바스켓 기준으로 3이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                        self.printt('(>= 3)선물매도 건수가 바스켓 기준으로 3이상이면 거래없음')
                        self.printt('또는 지난헤지비율 100이면 거래없음')
                        self.printt(myhave_sell_total_mall_basket_cnt_remove)
                        self.printt(last_option_s_hedge_ratio)

                        # 연결선물가상매매
                        SellBuyType = '매도'
                        # 시분초
                        current_time = QTime.currentTime()
                        text_time = current_time.toString('hh:mm:ss')
                        time_msg = ' 연결선물가상매매 : ' + text_time + ' 선물재고(' + str(
                            myhave_sell_total_mall_basket_cnt_remove) + \
                                   ')' + ' 지난헤지비율(' + str(last_option_s_hedge_ratio) + ')'
                        # 텍스트 저장 호출
                        self.printt_selled(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                        return
                    elif myhave_sell_total_mall_basket_cnt_remove == 2:
                        # # 옵션 종목검색(풋매도)
                        # put_or_call = 'put'
                        # if day_residue_int > 2:
                        #     month_mall_type = 'center_index'
                        #     # center_index / center_index_45
                        # else:
                        #     month_mall_type = 'center_index_45'
                        #     # center_index / center_index_45
                        #
                        # item_list_cnt_type = self.option_s_sell_items_search(myhave_sell_total_mall_cnt, put_or_call,
                        #                                                   month_mall_type)
                        # # print(item_list_cnt_type)
                        # # item_list_cnt_type = {'code_no': ['301V2337'], 'cnt': [3], 'sell_buy_type': [2]}      # option_s_sell_items_search 결과값
                        # self.printt('(== 2)옵션 종목검색(풋매도)')
                        # self.printt(item_list_cnt_type)
                        #
                        # # -----
                        # # 텍스트 저장은 종목이 있을경우에만
                        # if len(item_list_cnt_type['code_no']) > 0:
                        #     item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                        #     for i in range(len(item_list_cnt_type['code_no'])):
                        #         item_list_cnt_for_store['code_no'].append(item_list_cnt_type['code_no'][i])
                        #         item_list_cnt_for_store['cnt'].append(item_list_cnt_type['cnt'][i])
                        #     # 종목코드와 수량(텍스트에 저장하기)
                        #     self.today_put_order_list_text_store(item_list_cnt_for_store)
                        # # -----

                        # 일반 진입
                        self.printt('(== 2)옵션 진입없음, 일반 진입')
                        pass

                    elif myhave_sell_total_mall_basket_cnt_remove == 1:
                        # 일반 진입
                        self.printt('(== 1)옵션 진입없음, 일반 진입')
                        pass

                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
                    # print(item_list_cnt_type)

                elif myhave_buy_total_mall_cnt > 0:
                    self.printt('매수재고 있음')
                    self.printt('차월물만 청산')

                    # # -----
                    # # 만일 재고가 2이하 인데 옵션 재고가 있을 때
                    # for p in range(len(self.option_myhave['code'])):
                    #     # 선물재고는 pass
                    #     if self.option_myhave['code'][p][:3] == '101':
                    #         pass
                    #     # 재고가 혹시 매도
                    #     elif self.option_myhave['sell_or_buy'][p] == 1:
                    #         item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    #         item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    #         item_list_cnt_type['sell_buy_type'].append(2)
                    #     # 재고가 행여나 매수
                    #     elif self.option_myhave['sell_or_buy'][p] == 2:
                    #         item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    #         item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    #         item_list_cnt_type['sell_buy_type'].append(1)
                    # # -----

                    # 선물매도
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
                    # print(item_list_cnt_type)
            # 신호확인은 당월물로
            elif self.futrue_s_data['run_price'][0] < day_poly_min_price:
                self.printt('차월물만 재고있음 선물매수(2) 신호발생')
                # 선물(진입/청산) 신호발생시 db 저장
                signal_out = 2
                self.printt('# 선물(진입/청산) 신호발생시 db 저장')
                self.future_s_signal_out_store_fn(myhave_sell_total_mall_basket_cnt_remove,
                                                  myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int,
                                                  signal_out)
                # 재고수량 (매도/ 매수) 비교
                if myhave_sell_total_mall_cnt > 0:
                    self.printt('매도재고 있음')
                    self.printt('차월물만 청산')

                    # # -----
                    # # 만일 재고가 2이하 인데 옵션 재고가 있을 때
                    # for p in range(len(self.option_myhave['code'])):
                    #     # 선물재고는 pass
                    #     if self.option_myhave['code'][p][:3] == '101':
                    #         pass
                    #     # 재고가 혹시 매도
                    #     elif self.option_myhave['sell_or_buy'][p] == 1:
                    #         item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    #         item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    #         item_list_cnt_type['sell_buy_type'].append(2)
                    #     # 재고가 행여나 매수
                    #     elif self.option_myhave['sell_or_buy'][p] == 2:
                    #         item_list_cnt_type['code_no'].append(self.option_myhave['code'][p])
                    #         item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p])
                    #         item_list_cnt_type['sell_buy_type'].append(1)
                    # # -----

                    # 선물매수
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(2)
                    # print(item_list_cnt_type)

                elif myhave_buy_total_mall_cnt > 0:
                    self.printt('매수재고 있음')
                    self.printt('차월물만 진입')

                    # 선물재고 건수 및 옵션재고 확인
                    if myhave_buy_total_mall_basket_cnt_remove >= 3 or last_option_s_hedge_ratio == 100:
                        # 매수재고 : 매수신호 => 선물매수 건수가 바스켓 기준으로 3이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                        self.printt('(>= 3)선물매수 건수가 바스켓 기준으로 3이상이면 거래없음')
                        self.printt('또는 지난헤지비율 100이면 거래없음')
                        self.printt(myhave_sell_total_mall_basket_cnt_remove)
                        self.printt(last_option_s_hedge_ratio)

                        # 연결선물가상매매
                        SellBuyType = '매수'
                        # 시분초
                        current_time = QTime.currentTime()
                        text_time = current_time.toString('hh:mm:ss')
                        time_msg = ' 연결선물가상매매 : ' + text_time + ' 선물재고(' + str(
                            myhave_sell_total_mall_basket_cnt_remove) + \
                                   ')' + ' 지난헤지비율(' + str(last_option_s_hedge_ratio) + ')'
                        # 텍스트 저장 호출
                        self.printt_buyed(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                        return
                    elif myhave_buy_total_mall_basket_cnt_remove == 2:
                        # # 옵션 종목검색(콜매도)
                        # put_or_call = 'call'
                        # if day_residue_int > 2:
                        #     month_mall_type = 'center_index'
                        #     # center_index / center_index_45
                        # else:
                        #     month_mall_type = 'center_index_45'
                        #     # center_index / center_index_45
                        #
                        # item_list_cnt_type = self.option_s_sell_items_search(myhave_buy_total_mall_cnt, put_or_call,
                        #                                               month_mall_type)
                        # # print(item_list_cnt_type)
                        # # item_list_cnt_type = {'code_no': ['301V2337'], 'cnt': [3], 'sell_buy_type': [2]}      # option_s_sell_items_search 결과값
                        # self.printt('(== 2)옵션 종목검색(콜매도)')
                        # self.printt(item_list_cnt_type)
                        #
                        # # -----
                        # # 텍스트 저장은 종목이 있을경우에만
                        # if len(item_list_cnt_type['code_no']) > 0:
                        #     item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                        #     for i in range(len(item_list_cnt_type['code_no'])):
                        #         item_list_cnt_for_store['code_no'].append(item_list_cnt_type['code_no'][i])
                        #         item_list_cnt_for_store['cnt'].append(item_list_cnt_type['cnt'][i])
                        #     # 종목코드와 수량(텍스트에 저장하기)
                        #     self.today_call_order_list_text_store(item_list_cnt_for_store)
                        # # -----

                        # 일반 진입
                        self.printt('(== 2)옵션 진입없음, 일반 진입')
                        pass

                    elif myhave_buy_total_mall_basket_cnt_remove == 1:
                        # 일반 진입
                        self.printt('(== 1)옵션 진입없음, 일반 진입')
                        pass

                    # 선물매수
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(2)
                    # print(item_list_cnt_type)

        # 계좌내 당월물 & 차월물 재고없음
        else:
            # 바스켓 재설정
            # # 선옵계좌별주문가능수량요청
            # item_code = self.futrue_s_data['item_code'][0]
            # sell_or_buy_type = '1'  # 매도 매수 타입 # "매매구분"(1:매도, 2:매수)
            # price_type = '1'  # 주문유형 = 1:지정가, 3:시장가
            # item_order_price_six_digit = int(self.futrue_s_data['run_price'][0] * 1000)
            # # print(item_order_price_six_digit)
            # item_order_price_five_digit_str = str(item_order_price_six_digit)
            # # print(item_order_price_five_digit_str)
            # self.future_s_option_s_order_able_cnt_rq(item_code, sell_or_buy_type, price_type,
            #                                          item_order_price_five_digit_str)
            # # 신규가능수량
            # print('self.future_s_option_s_new_order_able_cnt')
            # print(self.future_s_option_s_new_order_able_cnt)

            # stock 추정예탁자산과 합쳐서 총 신규가능수량 다시 구하기
            # 선물 1건 계약시 필요증거금
            need_deposit_money = math.floor(
                self.order_able_cash / self.future_s_option_s_new_order_able_cnt)

            # 선물옵션 순자산금액 + stock 추정예탁자산
            option_have_money_plus_estimated_deposit = self.option_have_money + self.estimated_deposit

            # 선물옵션 + stock 총자산 / 선물 1건 계약시 필요증거금
            total_money_new_able_cnt = math.floor(option_have_money_plus_estimated_deposit / need_deposit_money)
            self.printt('total_money_new_able_cnt')
            self.printt(total_money_new_able_cnt)

            # 선물 레버리지(10 or 20) 결정
            if total_money_new_able_cnt < Future_s_Leverage_Int:
                basket_cnt = 1
            else:
                basket_cnt = math.floor(total_money_new_able_cnt / Future_s_Leverage_Int)
            self.printt('basket_cnt')
            self.printt(basket_cnt)
            # basket_cnt 텍스트 저장
            self.future_s_basket_cnt_text_store(basket_cnt)
            # 바스켓 재설정

            # 신규진입
            if self.futrue_s_data['run_price'][0] > day_poly_max_price:
                self.printt('당월물 재고없음 선물매도(1)(신규진입)')
                # 선물(진입/청산) 신호발생시 db 저장
                signal_out = 1
                self.printt('# 선물(진입/청산) 신호발생시 db 저장')
                self.future_s_signal_out_store_fn(myhave_sell_total_mall_basket_cnt_remove,
                                                  myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int,
                                                  signal_out)
                # 롤오버 감안 미리 차월물 진입 여부
                # 재고수량과 비교하여 잔존일이 2일 이상 남았으면 당월물 그렇지 않으면 차월물
                if future_s_day_residue_int > 2:
                    self.printt('당월물 진입')
                    item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
                elif future_s_day_residue_int <= 2:
                    self.printt('차월물 진입')
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
            elif self.futrue_s_data['run_price'][0] < day_poly_min_price:
                self.printt('당월물 재고없음 선물매수(2)(신규진입)')
                # 선물(진입/청산) 신호발생시 db 저장
                signal_out = 2
                self.printt('# 선물(진입/청산) 신호발생시 db 저장')
                self.future_s_signal_out_store_fn(myhave_sell_total_mall_basket_cnt_remove,
                                                  myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int,
                                                  signal_out)
                # 롤오버 감안 미리 차월물 진입 여부
                # 재고수량과 비교하여 잔존일이 2일 이상 남았으면 당월물 그렇지 않으면 차월물
                if future_s_day_residue_int > 2:
                    self.printt('당월물 진입')
                    item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(2)
                elif future_s_day_residue_int <= 2:
                    self.printt('차월물 진입')
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(2)
        self.printt('item_list_cnt_type :: future_s_market_ready 결과')
        self.printt(item_list_cnt_type)

        # 검색된 종목코드 여부
        item_list_cnt = len(item_list_cnt_type['code_no'])
        if item_list_cnt > 0:
            for i in range(len(item_list_cnt_type['code_no'])):
                self.item_list_cnt_type['code_no'].append(item_list_cnt_type['code_no'][i])
                self.item_list_cnt_type['cnt'].append(item_list_cnt_type['cnt'][i])
                self.item_list_cnt_type['sell_buy_type'].append(item_list_cnt_type['sell_buy_type'][i])
                self.item_list_cnt_type['state'].append(0)
                self.item_list_cnt_type['order_no'].append(0)

    # 선물(진입/청산) 신호발생시 db 저장
    def future_s_signal_out_store_fn(self, myhave_sell_total_mall_basket_cnt_remove, myhave_buy_total_mall_basket_cnt_remove, basket_cnt, day_residue_int, signal_out):
        # -----
        # db명
        # 파이썬 인터프리트가 현재 실행되고 있는 기계의 hostname을 스트링 형태로 return
        pc_host_name = socket.gethostname()
        pc_ip_address = socket.gethostbyname(pc_host_name)
        # print('현재 실행되고 있는 기계의 hostname / pc_ip_address')
        # print(pc_host_name)
        # print(pc_ip_address)
        db_name_future_s_signal_out_data = 'future_s_signal_out_store_' + pc_host_name
        # 딕셔너리 선언 / 저장준비
        future_s_signal_out_data = {'center_option_price': [], 'fu_run_price': [], 'sell_or_buy': [], 'myhave_fu_cnt': [], 'basket_cnt': [], 'day_residue_int': [], 'signal_out': []}
        future_s_signal_out_data['center_option_price'].append(self.center_option_price)
        future_s_signal_out_data['fu_run_price'].append(self.futrue_s_data['run_price'][0])
        if myhave_sell_total_mall_basket_cnt_remove > 0:
            sell_or_buy = 1
            myhave_total_mall_basket_cnt_remove = myhave_sell_total_mall_basket_cnt_remove
        elif myhave_buy_total_mall_basket_cnt_remove > 0:
            sell_or_buy = 2
            myhave_total_mall_basket_cnt_remove = myhave_buy_total_mall_basket_cnt_remove
        else:
            sell_or_buy = 0
            myhave_total_mall_basket_cnt_remove = 0
        future_s_signal_out_data['sell_or_buy'].append(sell_or_buy)
        future_s_signal_out_data['myhave_fu_cnt'].append(myhave_total_mall_basket_cnt_remove)
        future_s_signal_out_data['basket_cnt'].append(basket_cnt)
        future_s_signal_out_data['day_residue_int'].append(day_residue_int)
        future_s_signal_out_data['signal_out'].append(signal_out)
        # 저장 함수 호출
        future_s_signal_out_data_store(Folder_Name_DB_Store, db_name_future_s_signal_out_data, future_s_signal_out_data)
        # -----

    # 선물 롤오버
    def future_s_roll_over_fn(self, basket_cnt):
        # 주문변수 초기화
        item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 선물 영업일 기준 잔존일
        future_s_day_residue_int = self.futrue_s_data['day_residue'][0]  # int
        # print(future_s_day_residue_int)

        # 계좌내 선물 재고 확인
        myhave_sell_current_mall_cnt = 0
        myhave_buy_current_mall_cnt = 0
        myhave_sell_total_mall_cnt = 0
        myhave_buy_total_mall_cnt = 0
        for f in range(len(self.option_myhave['code'])):
            # 당월물
            if self.option_myhave['code'][f] == self.futrue_s_data['item_code'][0]:
                if self.option_myhave['sell_or_buy'][f] == 1:
                    myhave_sell_current_mall_cnt = myhave_sell_current_mall_cnt + self.option_myhave['myhave_cnt'][f]
                    myhave_sell_total_mall_cnt = myhave_sell_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
                elif self.option_myhave['sell_or_buy'][f] == 2:
                    myhave_buy_current_mall_cnt = myhave_buy_current_mall_cnt + self.option_myhave['myhave_cnt'][f]
                    myhave_buy_total_mall_cnt = myhave_buy_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
            # 차월물
            elif self.option_myhave['code'][f] == self.futrue_s_data_45['item_code'][0]:
                if self.option_myhave['sell_or_buy'][f] == 1:
                    myhave_sell_total_mall_cnt = myhave_sell_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
                elif self.option_myhave['sell_or_buy'][f] == 2:
                    myhave_buy_total_mall_cnt = myhave_buy_total_mall_cnt + self.option_myhave['myhave_cnt'][f]
        # print(myhave_sell_current_mall_cnt)
        # print(myhave_buy_current_mall_cnt)
        # print(myhave_sell_total_mall_cnt)
        # print(myhave_buy_total_mall_cnt)

        # 계좌내 선물 재고 확인
        # 계좌내 당월물 재고있음
        if self.futrue_s_data['item_code'][0] in self.option_myhave['code']:
            # roll_over 실행
            self.printt('# roll_over 실행')
            # 당월물 재고를 basket_cnt로 나눠서 그 값이 현재 선물 잔존일보다 크면 큰 만큼 청산
            if myhave_sell_current_mall_cnt > 0:
                self.printt('당월물 매도 재고 있음')
                sell_roll_over_check_cnt = int(myhave_sell_current_mall_cnt / basket_cnt)
                # 잔존일에서 (-2)를 빼서 차이 역수 롤오버 건수(담날꺼까지 롤오버)
                # 잔존일 1일이면 재고 모두
                if future_s_day_residue_int == 1:
                    roll_over_diff_cnt = sell_roll_over_check_cnt
                else:
                    roll_over_diff_cnt = ((future_s_day_residue_int - 2) - sell_roll_over_check_cnt) * (-1)
                self.printt(roll_over_diff_cnt)
                if roll_over_diff_cnt > 0:
                    self.printt('# roll_over 실행 조건 만족')
                    self.printt('당월물 매수(2) / 차월물 매도(1)')
                    item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt * roll_over_diff_cnt)
                    item_list_cnt_type['sell_buy_type'].append(2)
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt * roll_over_diff_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
            elif myhave_buy_current_mall_cnt > 0:
                self.printt('당월물 매수 재고 있음')
                buy_roll_over_check_cnt = int(myhave_buy_current_mall_cnt / basket_cnt)
                # 잔존일에서 (-2)를 빼서 차이 역수 롤오버 건수(담날꺼까지 롤오버)
                # 잔존일 1일이면 재고 모두
                if future_s_day_residue_int == 1:
                    roll_over_diff_cnt = buy_roll_over_check_cnt
                else:
                    roll_over_diff_cnt = ((future_s_day_residue_int - 2) - buy_roll_over_check_cnt) * (-1)
                self.printt(roll_over_diff_cnt)
                if roll_over_diff_cnt > 0:
                    self.printt('# roll_over 실행 조건 만족')
                    self.printt('당월물 매도(1) / 차월물 매수(2)')
                    item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt * roll_over_diff_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt * roll_over_diff_cnt)
                    item_list_cnt_type['sell_buy_type'].append(2)
        self.printt('item_list_cnt_type :: future_s_roll_over_fn 결과')
        self.printt(item_list_cnt_type)

        # 검색된 종목코드 여부
        item_list_cnt = len(item_list_cnt_type['code_no'])
        if item_list_cnt > 0:
            for i in range(len(item_list_cnt_type['code_no'])):
                self.item_list_cnt_type['code_no'].append(item_list_cnt_type['code_no'][i])
                self.item_list_cnt_type['cnt'].append(item_list_cnt_type['cnt'][i])
                self.item_list_cnt_type['sell_buy_type'].append(item_list_cnt_type['sell_buy_type'][i])
                self.item_list_cnt_type['state'].append(0)
                self.item_list_cnt_type['order_no'].append(0)

    # 주식매수 준비
    def stock_buy_ready_fn(self, stock_tarket_item_list):
        # # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        # if self.MarketEndingVar == '3':
        #     # 주식매수 종목검색
        #     self.stock_buy_items_search(stock_tarket_item_list)
        pass
        # 전단계로 보냄

    # 당일 매도 종목 찾기
    def selled_today_items_search_fn(self):
        selled_today_items = []
        # 폴더
        # Folder_Name_TXT_Store 폴더
        is_store_folder = os.path.isdir(Folder_Name_TXT_Store)
        if is_store_folder == False:
            return selled_today_items
        dir_list_year = os.listdir(Folder_Name_TXT_Store)
        # print(dir_list_year)

        # year 폴더
        folder_name_year = datetime.datetime.today().strftime("%Y")
        # File_Kind_Sell = 'selled' 파일 종류 불러오기
        selled_today_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + folder_name_year
        is_year_folder = os.path.isdir(selled_today_files_path)
        if is_year_folder == False:
            return selled_today_items
        dir_list_selled_today_files = os.listdir(selled_today_files_path)

        # selled 리스트 생성
        selled_today_list = []
        file_name_today = datetime.datetime.today().strftime("%Y%m%d")
        selled_today_file_txt_sum = File_Kind_Sell + '_' + file_name_today
        for f in dir_list_selled_today_files:
            if f.startswith(selled_today_file_txt_sum):
                selled_today_list.append(f)
        # print(selled_today_list)
        # 만일 오늘날자 매도 파일이 없으면 패스
        if len(selled_today_list) == 0:
            return selled_today_items

        # 당일 파일에서 종목코드 저장하기
        for file_name in selled_today_list:
            selled_today_file_path_name = selled_today_files_path + '/' + file_name
            f = open(selled_today_file_path_name, 'rt', encoding='UTF8')
            selleditems = f.readlines()
            f.close()
            for selleditem in selleditems:
                # print(selleditem)
                nselleditem = selleditem.split('::')[0]
                # print(nselleditem)
                selled_today_items.append(nselleditem)
                # print(selled_today_items)

        return selled_today_items

    # 당일 매수 종목 찾기
    def buyed_today_items_search_fn(self):
        buyed_today_items = []
        # 폴더
        # Folder_Name_TXT_Store 폴더
        is_store_folder = os.path.isdir(Folder_Name_TXT_Store)
        if is_store_folder == False:
            return buyed_today_items
        dir_list_year = os.listdir(Folder_Name_TXT_Store)
        # print(dir_list_year)

        # year 폴더
        folder_name_year = datetime.datetime.today().strftime("%Y")
        # File_Kind_Buy = 'buyed' 파일 종류 불러오기
        buyed_today_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + folder_name_year
        is_year_folder = os.path.isdir(buyed_today_files_path)
        if is_year_folder == False:
            return buyed_today_items
        dir_list_buyed_today_files = os.listdir(buyed_today_files_path)

        # buyed_selled 리스트 생성
        buyed_today_list = []
        file_name_today = datetime.datetime.today().strftime("%Y%m%d")
        buyed_today_file_txt_sum = File_Kind_Buy + '_' + file_name_today
        for f in dir_list_buyed_today_files:
            if f.startswith(buyed_today_file_txt_sum):
                buyed_today_list.append(f)
        # print(buyed_today_list)
        # 만일 오늘날자 매수 파일이 없으면 패스
        if len(buyed_today_list) == 0:
            return buyed_today_items

        # 당일 파일에서 종목코드 저장하기
        for file_name in buyed_today_list:
            buyed_today_file_path_name = buyed_today_files_path + '/' + file_name
            f = open(buyed_today_file_path_name, 'rt', encoding='UTF8')
            buyeditems = f.readlines()
            f.close()
            for buyeditem in buyeditems:
                nbuyeditem = buyeditem.split('::')[0]
                # print(nbuyeditem)
                buyed_today_items.append(nbuyeditem)

        return buyed_today_items

    # 선택종목 txt 호출
    def txt_pickup_for_choice_stock(self):
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

        # 10% 이하건수 변수 초기화
        self.fith_percent_high_cnt = 0
        self.ten_percent_low_cnt = 0
        # choice_stock 파일에서 종목코드 저장하기
        for file_name in choice_stock_list:
            choice_stock_file_path_name = choice_stock_files_path + '/' + file_name
            f = open(choice_stock_file_path_name, 'rt', encoding='UTF8')
            choice_stock_items = f.readlines()
            f.close()
            for choice_stock_item in choice_stock_items:
                item = choice_stock_item.split('\n')[0]
                # print(item)
                self.favorites_item_list.append(item[-6:])
                self.favorites_item_list_percent.append(item[-10:-8])
                # 15% 이상건수
                if int(item[-10:-8]) >= 15:
                    self.fith_percent_high_cnt += 1
                # 10% 이하건수
                if int(item[-10:-8]) < 15:
                    self.ten_percent_low_cnt += 1
        # print(self.favorites_item_list)
        # print(self.favorites_item_list_percent)


    # 월봉
    # 매도 최고가 / 매수 최고가 / 기울기 구하기
    def stock_trend_line_of_ai_month_data_fn(self):
        # 매도 최고가 / 매수 최고가 / 기울기 구하기
        stock_trend_line_of_ai_month = {'stock_no': [],
                                  'poly_sell_max_price': [], 'poly_buy_min_price': [],
                                  'sell_max_price': [], 'buy_min_price': [],
                                  'poly_h_gradient': [], 'poly_l_gradient': [],
                                  'h_gradient': [], 'l_gradient': []}
        # 폴더
        current_year = datetime.datetime.today().strftime("%Y")
        # print(current_year)
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # print(db_file_path)
        is_db_file = os.path.isdir(db_file_path)
        # print(is_db_file)
        if is_db_file == False:
            return

        # db명 설정
        db_name = 'stock_trend_line_of_ai_month' + '.db'
        # print(db_name)
        db_name_db = db_file_path + '/' + db_name
        # print(db_name_db)

        # 테이블명 가져오기
        con = sqlite3.connect(db_name_db)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name = cursor.fetchall()
        # print(total_table_name)
        if len(total_table_name) == 0:
            return

        table_name_list = []
        # 가장 최근일자 1건만 취하기
        table_name_list.append(total_table_name[-1][0])
        self.printt('stock_trend_line_of_ai_month 가장 최근 테이블')
        self.printt(table_name_list)
        # print('stock_trend_line_of_ai_month 가장 최근 테이블')
        # print(table_name_list)

        # 데이타 가져오기 함수 호출
        for table_name in table_name_list:
            data_pickup_ret = data_pickup(db_name_db, table_name)
            # print(table_name)
            # print(data_pickup_ret)
            stock_no = data_pickup_ret['stock_no'].values
            poly_sell_max_price = data_pickup_ret['poly_sell_max_price'].values
            poly_buy_min_price = data_pickup_ret['poly_buy_min_price'].values
            sell_max_price = data_pickup_ret['sell_max_price'].values
            buy_min_price = data_pickup_ret['buy_min_price'].values
            poly_h_gradient = data_pickup_ret['poly_h_gradient'].values
            poly_l_gradient = data_pickup_ret['poly_l_gradient'].values
            h_gradient = data_pickup_ret['h_gradient'].values
            l_gradient = data_pickup_ret['l_gradient'].values

            for i in range(len(stock_no)):
                # 테이타 생성
                stock_trend_line_of_ai_month['stock_no'].append(stock_no[i])
                stock_trend_line_of_ai_month['poly_sell_max_price'].append(poly_sell_max_price[i])
                stock_trend_line_of_ai_month['poly_buy_min_price'].append(poly_buy_min_price[i])
                stock_trend_line_of_ai_month['sell_max_price'].append(sell_max_price[i])
                stock_trend_line_of_ai_month['buy_min_price'].append(buy_min_price[i])
                stock_trend_line_of_ai_month['poly_h_gradient'].append(poly_h_gradient[i])
                stock_trend_line_of_ai_month['poly_l_gradient'].append(poly_l_gradient[i])
                stock_trend_line_of_ai_month['h_gradient'].append(h_gradient[i])
                stock_trend_line_of_ai_month['l_gradient'].append(l_gradient[i])
        # print(stock_trend_line_of_ai_month)
        # db닫기
        con.commit()
        con.close()
        return stock_trend_line_of_ai_month

    # 일봉
    # 매도 최고가 / 매수 최고가 / 기울기 구하기
    def stock_trend_line_of_ai_day_data_fn(self):
        # 매도 최고가 / 매수 최고가 / 기울기 구하기
        stock_trend_line_day_total = {'stock_no': [],
                                      'poly_sell_max_price': [], 'poly_buy_min_price': [],
                                      'sell_max_price': [], 'buy_min_price': [],
                                      'poly_h_gradient': [], 'poly_l_gradient': [],
                                      'h_gradient': [], 'l_gradient': []}
        stock_trend_line_of_ai_day = {'stock_no': [],
                                      'poly_sell_max_price': [], 'poly_buy_min_price': [],
                                      'sell_max_price': [], 'buy_min_price': [],
                                      'poly_h_gradient': [], 'poly_l_gradient': [],
                                      'h_gradient': [], 'l_gradient': []}
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(os.getcwd() + '/' + Folder_Name_DB_Store)
        if is_store_folder == False:
            os.mkdir(os.getcwd() + '/' + Folder_Name_DB_Store)

        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # print(db_file_path)
        is_db_file = os.path.isdir(db_file_path)
        # print(is_db_file)
        if is_db_file == False:
            return stock_trend_line_of_ai_day

        # db명 설정
        # 월봉도 추가(20240116) <= 제거(왜냐하면 1개월 내내 신호가 나올수 있음)20240116  'stock_trend_line_of_ai_month.db',
        db_name_lists = ['stock_trend_line_of_ai_day.db']
        for db_name in db_name_lists:
            # db_name = 'stock_trend_line_of_ai_day' + '.db'
            # print(db_name)
            db_name_db = db_file_path + '/' + db_name
            # print(db_name_db)
            # 테이블명 가져오기
            con = sqlite3.connect(db_name_db)
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            total_table_name = cursor.fetchall()
            # print(total_table_name)

            if len(total_table_name) == 0:
                return stock_trend_line_of_ai_day

            table_name_list = []
            # 가장 최근일자 1건만 취하기
            table_name_list.append(total_table_name[-1][0])
            # table_name_list.append(total_table_name[-2][0])
            # self.printt('stock_trend_line_of_ai_day 가장 최근 테이블 1건')
            # self.printt(table_name_list)
            # print('stock_trend_line_of_ai_day 가장 최근 테이블 1건')
            # print(table_name_list)

            # -----
            # 데이타 가져오기 함수 호출
            for table_name in table_name_list:
                data_pickup_ret = data_pickup(db_name_db, table_name)
                # print(table_name)
                # print(data_pickup_ret)
                stock_no = data_pickup_ret['stock_no'].values
                poly_sell_max_price = data_pickup_ret['poly_sell_max_price'].values
                poly_buy_min_price = data_pickup_ret['poly_buy_min_price'].values
                sell_max_price = data_pickup_ret['sell_max_price'].values
                buy_min_price = data_pickup_ret['buy_min_price'].values
                poly_h_gradient = data_pickup_ret['poly_h_gradient'].values
                poly_l_gradient = data_pickup_ret['poly_l_gradient'].values
                h_gradient = data_pickup_ret['h_gradient'].values
                l_gradient = data_pickup_ret['l_gradient'].values
                # 전체 데이타 생성
                for i in range(len(stock_no)):
                    stock_trend_line_day_total['stock_no'].append(stock_no[i])
                    stock_trend_line_day_total['poly_sell_max_price'].append(poly_sell_max_price[i])
                    stock_trend_line_day_total['poly_buy_min_price'].append(poly_buy_min_price[i])
                    stock_trend_line_day_total['sell_max_price'].append(sell_max_price[i])
                    stock_trend_line_day_total['buy_min_price'].append(buy_min_price[i])
                    stock_trend_line_day_total['poly_h_gradient'].append(poly_h_gradient[i])
                    stock_trend_line_day_total['poly_l_gradient'].append(poly_l_gradient[i])
                    stock_trend_line_day_total['h_gradient'].append(h_gradient[i])
                    stock_trend_line_day_total['l_gradient'].append(l_gradient[i])
            # print(stock_trend_line_day_total)
            # db닫기
            con.commit()
            con.close()
        # -----

        # -----
        # 종목코드 만들기(중복제거)
        stock_trend_line_day_each_code = []
        for i in range(len(stock_trend_line_day_total['stock_no'])):
            if stock_trend_line_day_total['stock_no'][i] in stock_trend_line_day_each_code:
                pass
            else:
                stock_trend_line_day_each_code.append(stock_no[i])
        # print(stock_trend_line_day_each_code)
        # -----

        # -----
        # 만들어진 종목코드 기준으로 데이타 각각 저장
        for code in stock_trend_line_day_each_code:
            poly_sell_max_price = []
            poly_buy_min_price = []
            sell_max_price = []
            buy_min_price = []
            poly_h_gradient = []
            poly_l_gradient = []
            h_gradient = []
            l_gradient = []
            for i in range(len(stock_trend_line_day_total['stock_no'])):
                if code == stock_trend_line_day_total['stock_no'][i]:
                    poly_sell_max_price.append(stock_trend_line_day_total['poly_sell_max_price'][i])
                    poly_buy_min_price.append(stock_trend_line_day_total['poly_buy_min_price'][i])
                    sell_max_price.append(stock_trend_line_day_total['sell_max_price'][i])
                    buy_min_price.append(stock_trend_line_day_total['buy_min_price'][i])
                    poly_h_gradient.append(stock_trend_line_day_total['poly_h_gradient'][i])
                    poly_l_gradient.append(stock_trend_line_day_total['poly_l_gradient'][i])
                    h_gradient.append(stock_trend_line_day_total['h_gradient'][i])
                    l_gradient.append(stock_trend_line_day_total['l_gradient'][i])
            stock_trend_line_of_ai_day['stock_no'].append(code)
            stock_trend_line_of_ai_day['poly_sell_max_price'].append(min(poly_sell_max_price))
            stock_trend_line_of_ai_day['poly_buy_min_price'].append(max(poly_buy_min_price))
            stock_trend_line_of_ai_day['sell_max_price'].append(min(sell_max_price))
            stock_trend_line_of_ai_day['buy_min_price'].append(max(buy_min_price))
            stock_trend_line_of_ai_day['poly_h_gradient'].append(min(poly_h_gradient))
            stock_trend_line_of_ai_day['poly_l_gradient'].append(max(poly_l_gradient))
            stock_trend_line_of_ai_day['h_gradient'].append(min(h_gradient))
            stock_trend_line_of_ai_day['l_gradient'].append(max(l_gradient))
        # print(stock_trend_line_of_ai_day)
        # -----

        # self.printt('# stock_trend_line_of_ai_day')
        # self.printt(stock_trend_line_of_ai_day)

        return stock_trend_line_of_ai_day

    # stock_have_data db
    def stock_have_db_pickup(self, db_name):
        # 폴더
        # db_store 폴더
        is_store_folder = os.path.isdir(Folder_Name_DB_Store)
        if is_store_folder == False:
            return
        dir_list_year = os.listdir(Folder_Name_DB_Store)
        # print(dir_list_year)
        # # 폴더
        # current_year = datetime.datetime.today().strftime("%Y")
        # # print(current_year)
        # db_file_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + current_year
        # is_db_file = os.path.isdir(db_file_path)
        # if is_db_file == False:
        #     return
        # db명 설정
        # stock_have_data는 년 이월하면 않되므로
        db_name_db = Folder_Name_DB_Store + '/' + db_name + '.db'
        # print(db_name_db)

        # 테이블명 가져오기
        con = sqlite3.connect(db_name_db)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name = cursor.fetchall()
        # print(total_table_name)
        # db 테이블 꺼꾸로 뒤집음
        total_table_name.reverse()

        table_name_list = []
        for i in range(len(total_table_name)):
            table_name_list.append(total_table_name[i][0])
            if i == Buy_Item_Max_Cnt - 1:
                break
        # 테이블 다시 꺼꾸로 뒤집음
        table_name_list.reverse()
        self.printt('테이블명 가져오기')
        self.printt(table_name_list)

        # 일별누적
        last_stock_have_data = {'stock_no': [], 'stock_name': [], 'market_in_price': [], 'myhave_cnt': [], 'run_price': []}
        # 데이타 가져오기 함수 호출
        data_pickup_ret_cnt = 0
        for table_name in table_name_list:
            data_pickup_ret = data_pickup(db_name_db, table_name)
            # print(data_pickup_ret)
            # 최종 저장시간
            data_pickup_ret_cnt = len(data_pickup_ret['time'])

        # 호출데이타 있을때만 실행
        if data_pickup_ret_cnt != 0:
            select_time = data_pickup_ret['time'][data_pickup_ret_cnt - 1]
            # print(select_time)
            # 선택시간 기준으로 데이타 수집
            select_time_df_read = data_pickup_ret[data_pickup_ret['time'] == select_time]
            data_pickup_ret_cnt_minus = data_pickup_ret_cnt - len(select_time_df_read['time'])
            # print(select_time_df_read)

            # stock_have_data append
            for i in range(data_pickup_ret_cnt_minus, data_pickup_ret_cnt):
                last_stock_have_data['stock_no'].append(str(data_pickup_ret['stock_no'][i]))
                last_stock_have_data['stock_name'].append(str(data_pickup_ret['stock_name'][i]))
                last_stock_have_data['market_in_price'].append(abs(int(data_pickup_ret['market_in_price'][i])))
                last_stock_have_data['myhave_cnt'].append(abs(int(data_pickup_ret['myhave_cnt'][i])))
                last_stock_have_data['run_price'].append(abs(int(data_pickup_ret['run_price'][i])))
        # db닫기
        con.commit()
        con.close()
        return last_stock_have_data

    # 리스트 뿌리기
    def stock_listed_slot(self, stock_have_data):
        # 테이블 위젯에 리스트 뿌리기
        self.tableWidget_myhame.setRowCount(len(stock_have_data['stock_no']))

        for i in range(len(stock_have_data['stock_no'])):
            str_stock_name = str(stock_have_data['stock_name'][i])
            # str_stock_no = str(stock_have_data['stock_no'][i])
            str_myhave_cnt = str(stock_have_data['myhave_cnt'][i])
            str_market_in_price = str(stock_have_data['market_in_price'][i])
            str_run_price = str(stock_have_data['run_price'][i])

            self.tableWidget_myhame.setItem(i, 0, QTableWidgetItem(str_stock_name))
            # self.tableWidget_myhame.setItem(i, 1, QTableWidgetItem(str_stock_no))
            self.tableWidget_myhame.setItem(i, 1, QTableWidgetItem(str_myhave_cnt))
            self.tableWidget_myhame.setItem(i, 2, QTableWidgetItem(str_market_in_price))
            self.tableWidget_myhame.setItem(i, 3, QTableWidgetItem(str_run_price))

        # # 차트 그리기
        # self.draw_chart(table_name, select_time_df_read, min_index, Chart_Ylim, Up_CenterOption_Down)

    # 장중 체크
    def running_market_fn(self):
        # 09시 이후 18시 이전, 장마감 신호 '3'
        # 시분초
        current_time = QTime.currentTime()
        text_time = current_time.toString('hh')
        hour_time_int = int(text_time)
        if (hour_time_int < 9) or (self.MarketEndingVar != '3') or (hour_time_int > 17):
            return False
        else:
            return True

    # 딕셔너리 큰것부터 정렬 건수만큼 코드만 보냄
    def dic_sort_fn(self, dic_data, item_cnt):
        # 정렬
        sorted_item_dic = {'stock_no': [], 'value': []}
        # 체결강도 기준초과 종목 리스트에 저장(정렬)
        for i in range(len(dic_data['stock_no'])):
            # 저장하려는 딕셔너리 갯수 0이면 무조건 append
            if len(sorted_item_dic['stock_no']) == 0:
                sorted_item_dic['stock_no'].append(dic_data['stock_no'][i])
                sorted_item_dic['value'].append(dic_data['value'][i])
            elif len(sorted_item_dic['stock_no']) == 1:
                if sorted_item_dic['value'][-1] < dic_data['value'][i]:
                    sorted_item_dic['stock_no'].insert(0, dic_data['stock_no'][i])
                    sorted_item_dic['value'].insert(0, dic_data['value'][i])
                else:
                    sorted_item_dic['stock_no'].append(dic_data['stock_no'][i])
                    sorted_item_dic['value'].append(dic_data['value'][i])
            else:
                for j in range(len(sorted_item_dic['stock_no']) - 1):
                    if sorted_item_dic['value'][0] < dic_data['value'][i]:
                        sorted_item_dic['stock_no'].insert(0, dic_data['stock_no'][i])
                        sorted_item_dic['value'].insert(0, dic_data['value'][i])
                        break
                    elif sorted_item_dic['value'][-1] >= dic_data['value'][i]:
                        sorted_item_dic['stock_no'].append(dic_data['stock_no'][i])
                        sorted_item_dic['value'].append(dic_data['value'][i])
                        break
                    elif (sorted_item_dic['value'][j] >= dic_data['value'][i]) and \
                            (dic_data['value'][i] > sorted_item_dic['value'][j + 1]):
                        sorted_item_dic['stock_no'].insert(j + 1, dic_data['stock_no'][i])
                        sorted_item_dic['value'].insert(j + 1, dic_data['value'][i])
                        break

        # 정렬된 체결강도 다시 종목코드만 저장
        sorted_item_dic_for_cnt = []
        # 최대 매수목록
        for i in range(len(sorted_item_dic['stock_no'])):
            # 1회 최대 매수목록
            if i >= item_cnt:
                continue
            else:
                sorted_item_dic_for_cnt.append(sorted_item_dic['stock_no'][i])

        return sorted_item_dic_for_cnt

    # 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
    def stock_shlc_store_for_ai_fn(self, current_today, choice_stock_filename, db_name_db_month, db_name_db_day):
        # 텍스트파일에서 종목데이타 저장하기
        self.stock_item_data = {'stock_item_no': [], 'stock_item_name': [], 'stock_start': [], 'stock_high': [], 'stock_low': [],
                                        'stock_end': [], 'vol_cnt': []}

        # 선택종목
        choice_stock_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store
        dir_list_files = os.listdir(choice_stock_files_path)
        # choice_stock_list 리스트 생성
        choice_stock_list = []
        for f in dir_list_files:
            if f.startswith(choice_stock_filename):
                choice_stock_list.append(f)
        # print(choice_stock_list)
        # choice_stock 파일이 없으면 패스
        if len(choice_stock_list) == 0:
            return

        # 텍스트파일에서 종목데이타 저장하기
        for file_name in choice_stock_list:
            choice_stock_file_path_name = choice_stock_files_path + '/' + file_name
            f = open(choice_stock_file_path_name, 'rt', encoding='UTF8')
            choice_stock_items = f.readlines()
            f.close()
            for choice_stock_item in choice_stock_items:
                item = choice_stock_item.split('::')
                # print(item)
                self.stock_item_data['stock_item_no'].append(item[2].strip('\n'))
                self.stock_item_data['stock_item_name'].append(item[0])

        ref_day = current_today
        end_day = current_today
        # print(ref_day)
        # 주식월봉차트조회요청
        for stock_code in self.stock_item_data['stock_item_no']:
            # stock_code = '035600'

            # 주식월봉차트조회요청
            self.stock_shlc_month_data_fn(stock_code, ref_day, end_day)
            # print(self.output_stock_shlc_month_data)

            # 저장
            df = pd.DataFrame(self.output_stock_shlc_month_data,
                              columns=['stock_start', 'stock_high', 'stock_low', 'stock_end', 'vol_cnt'
                                       ],
                              index=self.output_stock_shlc_month_data['stock_date'])
            # db 연결하기
            con = sqlite3.connect(db_name_db_month)
            df.to_sql(stock_code, con, if_exists='replace', index_label='stock_date')
            # 'append'는 테이블이 존재하면 데이터만을 추가
            # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
            # index_label 인덱스 칼럼에 대한 라벨을 지정
            # db닫기
            con.commit()
            con.close()

        # 주식일봉차트조회요청
        for stock_code in self.stock_item_data['stock_item_no']:
            # stock_code = '035600'

            # 주식일봉차트조회요청
            self.stock_shlc_day_data_fn(stock_code, current_today)
            # print(self.output_stock_shlc_day_data)

            # 저장
            df = pd.DataFrame(self.output_stock_shlc_day_data,
                              columns=['stock_start', 'stock_high', 'stock_low', 'stock_end', 'vol_cnt'
                                       ],
                              index=self.output_stock_shlc_day_data['stock_date'])
            # db 연결하기
            con = sqlite3.connect(db_name_db_day)
            df.to_sql(stock_code, con, if_exists='replace', index_label='stock_date')
            # 'append'는 테이블이 존재하면 데이터만을 추가
            # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
            # index_label 인덱스 칼럼에 대한 라벨을 지정
            # db닫기
            con.commit()
            con.close()

        self.printt('self.stock_item_data')
        self.printt(len(self.stock_item_data['stock_item_no']))
        self.printt(self.stock_item_data)
        self.printt('stock_shlc db테이블 모두 완료')

        # 즐겨찾기 모든종목 실시간 정보를 받기 위해서는 주식일봉차트조회요청 이외에 체결강도조회 해야함
        # 체결강도조회 - 이벤트 슬롯 - 관심종목 조회함수 활용(거래량, 매도호가, 매수호가, 체결강도)
        transCode = ''
        transCode_cnt = 0
        for code in self.stock_item_data['stock_item_no']:
            # print(code)
            transCode = transCode + code + ';'
            transCode_cnt += 1
        self.printt('체결강도조회')
        self.printt(transCode_cnt)
        self.printt(transCode)
        self.deal_power_trans_fn(transCode, transCode_cnt)

    def stock_shlc_store_for_ai_realtime_fn(self, current_today, choice_stock_filename, db_name_db_month, db_name_db_day):
        # 선택종목
        # 주식일봉(실시간 모니터))
        for i in range(len(self.stock_item_data['stock_item_no'])):
            # stock_code = '035600'

            # -----
            con = sqlite3.connect(db_name_db_day)
            df_read = pd.read_sql("SELECT * FROM " + "'" + self.stock_item_data['stock_item_no'][i] + "'", con, index_col=None)
            # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
            # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당

            # print(df_read.iloc[0]['stock_date'])
            # print(df_read.iloc[0]['vol_cnt'])

            # 마지막날자를 현재 실시간 price로 변경
            # Pandas에서 인덱스 목록을 drop() 메소드의 매개변수로 넘겨서 일련의 행을 제거
            df_read.drop([0, 0], axis=0, inplace=True)

            # 실시간 price로 변경
            stock_date = current_today
            stock_code = self.stock_item_data['stock_item_no'][i]
            stock_start = self.stock_item_data['stock_start'][i]
            stock_high = self.stock_item_data['stock_high'][i]
            stock_low = self.stock_item_data['stock_low'][i]
            stock_end = self.stock_item_data['stock_end'][i]
            vol_cnt = self.stock_item_data['vol_cnt'][i]

            new_row = pd.DataFrame([[stock_date, stock_start, stock_high, stock_low, stock_end, vol_cnt]], columns=df_read.columns)
            output_stock_shlc_day_data = pd.concat([df_read.iloc[:0], new_row, df_read.iloc[0:]], ignore_index=True)
            # print(output_stock_shlc_day_data)
            # -----

            # 저장
            # df = pd.DataFrame(output_stock_shlc_day_data,
            #                   columns=['stock_start', 'stock_high', 'stock_low', 'stock_end', 'vol_cnt'
            #                            ],
            #                   index=output_stock_shlc_day_data['stock_date'])
            # # db 연결하기
            # con = sqlite3.connect(db_name_db_day)
            output_stock_shlc_day_data.to_sql(stock_code, con, if_exists='replace', index=None)
            # 'append'는 테이블이 존재하면 데이터만을 추가
            # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
            # index_label 인덱스 칼럼에 대한 라벨을 지정
            # db닫기
            con.commit()
            con.close()

        self.printt('self.stock_item_data')
        self.printt(len(self.stock_item_data['stock_item_no']))
        self.printt(self.stock_item_data)
        self.printt('(실시간)stock_shlc db테이블 모두 완료')

    # 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
    def future_s_store_for_ai_fn(self, current_today, choice_chain_future_s_item_code, db_name_db_month, db_name_db_day):
        # 선물월차트요청
        for future_s_code in choice_chain_future_s_item_code:
            # future_s_code = '10100000'
            # print(future_s_code)

            # 선물월차트요청
            self.future_s_shlc_month_data_fn(future_s_code, current_today)

            # 저장
            df = pd.DataFrame(self.output_future_s_chain_shlc_month_data,
                              columns=['stock_start', 'stock_high', 'stock_low', 'stock_end', 'vol_cnt'
                                       ],
                              index=self.output_future_s_chain_shlc_month_data['stock_date'])
            # db 연결하기
            con = sqlite3.connect(db_name_db_month)
            df.to_sql(future_s_code, con, if_exists='replace', index_label='stock_date')
            # 'append'는 테이블이 존재하면 데이터만을 추가
            # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
            # index_label 인덱스 칼럼에 대한 라벨을 지정
            # db닫기
            con.commit()
            con.close()

        # 선물일차트요청
        for future_s_code in choice_chain_future_s_item_code:
            # future_s_code = '10100000'

            # 선물일차트요청
            self.future_s_shlc_day_data_fn(future_s_code, current_today)

            # 저장
            df = pd.DataFrame(self.output_future_s_chain_shlc_day_data,
                              columns=['stock_start', 'stock_high', 'stock_low', 'stock_end',
                                       ],
                              index=self.output_future_s_chain_shlc_day_data['stock_date'])
            # db 연결하기
            con = sqlite3.connect(db_name_db_day)
            df.to_sql(future_s_code, con, if_exists='replace', index_label='stock_date')
            # 'append'는 테이블이 존재하면 데이터만을 추가
            # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
            # index_label 인덱스 칼럼에 대한 라벨을 지정
            # db닫기
            con.commit()
            con.close()

        self.printt('self.futrue_s_data')
        self.printt(len(self.futrue_s_data['item_code']))
        self.printt(self.futrue_s_data)
        self.printt('future_s_shlc db테이블 모두 완료')

    def future_s_store_for_ai_realtime_fn(self, current_today, choice_chain_future_s_item_code, db_name_db_month, db_name_db_day):
        # 선물일차트요청
        for i in range(len(choice_chain_future_s_item_code)):
            # future_s_code = '10100000'

            # -----
            con = sqlite3.connect(db_name_db_day)
            df_read = pd.read_sql("SELECT * FROM " + "'" + choice_chain_future_s_item_code[i] + "'", con, index_col=None)
            # 종목 코드가 숫자 형태로 구성돼 있으므로 한 번 작은따옴표로 감싸
            # index_col 인자는 DataFrame 객체에서 인덱스로 사용될 칼럼을 지정.  None을 입력하면 자동으로 0부터 시작하는 정숫값이 인덱스로 할당

            # print(df_read.iloc[0]['stock_date'])
            # print(df_read.iloc[0]['vol_cnt'])

            # 마지막날자를 현재 실시간 price로 변경
            # Pandas에서 인덱스 목록을 drop() 메소드의 매개변수로 넘겨서 일련의 행을 제거
            df_read.drop([0, 0], axis=0, inplace=True)

            # 실시간 price로 변경
            stock_date = current_today
            stock_code = choice_chain_future_s_item_code[i]
            stock_start = self.futrue_s_data['start_price'][i]
            stock_high = self.futrue_s_data['high_price'][i]
            stock_low = self.futrue_s_data['low_price'][i]
            stock_end = self.futrue_s_data['run_price'][i]
            # vol_cnt = self.futrue_s_data['vol_cnt'][i]

            new_row = pd.DataFrame([[stock_date, stock_start, stock_high, stock_low, stock_end]], columns=df_read.columns)
            output_future_s_chain_shlc_day_data = pd.concat([df_read.iloc[:0], new_row, df_read.iloc[0:]], ignore_index=True)
            # print(output_future_s_chain_shlc_day_data)
            # -----

            # # 저장
            # df = pd.DataFrame(self.output_future_s_chain_shlc_day_data,
            #                   columns=['stock_start', 'stock_high', 'stock_low', 'stock_end',
            #                            ],
            #                   index=self.output_future_s_chain_shlc_day_data['stock_date'])
            # # db 연결하기
            # # db 연결하기
            # con = sqlite3.connect(db_name_db_day)
            output_future_s_chain_shlc_day_data.to_sql(stock_code, con, if_exists='replace', index=None)
            # 'append'는 테이블이 존재하면 데이터만을 추가
            # 'replace'는 테이블이 존재하면 기존 테이블을 삭제하고 새로 테이블을 생성한 후 데이터를 삽입
            # index_label 인덱스 칼럼에 대한 라벨을 지정
            # db닫기
            con.commit()
            con.close()

        self.printt('self.futrue_s_data')
        self.printt(len(self.futrue_s_data['item_code']))
        self.printt(self.futrue_s_data)
        self.printt('(실시간)future_s_shlc db테이블 모두 완료')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()