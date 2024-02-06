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
# 1틱단계
One_Tick_Step = 0.01
# 기조자산 범위
Basic_Property_Range = 2.5
# 기조자산 1틱단계
Basic_Property_One_Tick_Step = 0.05
# 중심가 기준 위아래 몇칸을 뒤질까요?
Up_CenterOption_Down = 9
# 중심가 기준 위아래 모니터 건수
Up2_CenterOption_Down2 = 2

# 그래프 세로 칸수
Chart_Ylim = 12

# 연결선물
Chain_Future_s_Item_Code = ['10100000']

# 선물 레버리지(10 or 20) 결정(*** 향후 투자금액이 커지면 ~20으로 변경 :: 1 ~ 2 계약 바스켓 정도는 추가증거금 감당가능 판단 :: 20220316)
# 202209~ 옵션 매도 헷지방식으로 변경하면서 자산배정 변경(선물 4건, 매도 헷지 4블럭, 여분 4블럭)
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
        self.setWindowTitle('fuon(선물 트레이딩 & 옵션 매도 헷지 :: 주식 트레이딩(2/12))')

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
        # self.timer1.start(1000)
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
        # 가져오기 함수
        self.pushButton_datapickup_future_s_M.clicked.connect(self.data_pickup_future_s_chain_month_select_fill)
        self.pushButton_datapickup_future_s_D.clicked.connect(self.data_pickup_future_s_chain_day_select_fill)
        # currentIndexChanged 이벤트 핸들러
        self.comboBox_future_s_chain_month.activated.connect(self.data_pickup_future_s_chain_month)
        # currentIndexChanged 이벤트 핸들러
        self.comboBox_future_s_chain_day.activated.connect(self.data_pickup_future_s_chain_day)
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

        # 수동주문 시장 진입/청산
        # 클릭 불가능
        self.pushButton_fu_buy_have.setEnabled(False)
        self.pushButton_fu_sell_have.setEnabled(False)
        self.pushButton_call_item_list.setEnabled(False)
        self.pushButton_put_item_list.setEnabled(False)
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

        # 주문 테스트
        self.pushButton_3.clicked.connect(self.test)

        # 장마감 C=>CF
        self.pushButton_c_to_cf.clicked.connect(self.c_to_cf_hand)

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
        # [실시간 조회] 체크박스 무조건 켜놓기
        self.checkbox_realtime.setChecked(True)
        # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        self.MarketEndingVar = '3'
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

        # 선옵잔고요청 변수선언
        # 주문시 선옵잔고 변수 초기화
        self.reset_myhave_var()

        # 자료요청전 또는 장시작 전에 실시간신호 에러 방지를 위하여 부팅시 변수선언 먼저함
        # 인스턴스 변수 선언
        self.futrue_s_reset_output()
        # 인스턴스 변수 선언
        self.option_reset_output()

        # 주문 실행 결과
        # 인스턴스 변수 선언
        self.reset_order_var()
        # 주문 실행 결과
        # 인스턴스 변수 선언
        self.reset_order_var_stock()

        # 인스턴스 변수 선언
        self.stock_have_data_reset_output()

        # 선물전체시세요청
        self.futrue_s_data_rq()
        # 콜/풋 월별시세요청
        self.call_put_data_rq()

        # 옵션매도주문증거금 요청
        self.option_s_sell_deposit_money_data_rq()

        # 롤오버 변수 False :: 선물 롤오버 함수 입장 가능
        self.future_s_roll_over_run_var = False
        # 롤오버 변수 False :: 옵션 롤오버 함수 입장 가능
        self.option_s_roll_over_run_var = False

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

    # 입력데이터 서버전송(OPT50030 : 선물옵션일차트요청)
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

    # 계좌평가잔고내역요청
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
        else:
            self.remained_data = False

        if rqname == "선물전체시세요청":
            self._OPTFOFID(rqname, trcode)
        elif rqname == "선물전체시세요청_45":
            self._OPTFOFID_45(rqname, trcode)
        elif rqname == "선물월차트요청":
            self._opt50072(rqname, trcode)
        elif rqname == "선물옵션일차트요청":
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

        try:
            self.tr_event_loop.exit()
        except AttributeError:
            pass

# 서버 수신 데이타 처리

    # _OPTFOFID(선물전체시세요청)
    def _OPTFOFID(self, rqname, trcode):
        self.option_price_rows = self._get_repeat_cnt(trcode, rqname)

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
        self.option_price_rows = self._get_repeat_cnt(trcode, rqname)

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
            self.output_call_option_data['future_s'].append(self.futrue_s_data['run_price'][0])
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
            self.output_put_option_data['future_s'].append(self.futrue_s_data['run_price'][0])
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
            self.output_call_option_data_45['future_s'].append(self.futrue_s_data['run_price'][0])
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
            self.output_put_option_data_45['future_s'].append(self.futrue_s_data['run_price'][0])
            self.output_put_option_data_45['k200_s'].append(abs(float(0)))
            # (풋종목결제월별시세요청_45)::체결강도조회 강제로 0 바인딩
            self.output_put_option_data_45['deal_power'].append(abs(float(0)))

    # _opw20015(옵션매도주문증거금)
    def _opw20015(self, rqname, trcode):
        # 조회건수
        option_s_sell_deposit_money_rows = self._get_repeat_cnt(trcode, rqname)

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

# _opw00018(계좌평가잔고내역요청)
    def _opw00018(self, rqname, trcode):
        stock_data_rows = self._get_repeat_cnt(trcode, rqname)
        # print(stock_data_rows)

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
            # 강제로 0 바인딩
            self.stock_have_data['sell_price'].append(abs(int(0)))
            self.stock_have_data['sell_cnt'].append(abs(int(0)))
            self.stock_have_data['buy_price'].append(abs(int(0)))
            self.stock_have_data['buy_cnt'].append(abs(int(0)))
            self.stock_have_data['vol_cnt'].append(abs(int(0)))
            # ::체결강도조회 강제로 0 바인딩
            self.stock_have_data['deal_power'].append(abs(float(0)))

    # _opt50033(영업일기준잔존일)
    def _opt50033(self, rqname, trcode):
        day_residue = self._comm_get_data(trcode, "", rqname, 0, "영업일기준잔존일")
        for i in range(self.option_price_rows):
            self.output_call_option_data['day_residue'].append(abs(int(day_residue)))
            self.output_put_option_data['day_residue'].append(abs(int(day_residue)))

        # 차월물
        for i in range(self.option_price_rows_45):
            self.output_call_option_data_45['day_residue'].append(abs(int(day_residue)))
            self.output_put_option_data_45['day_residue'].append(abs(int(day_residue)))

    # 선옵잔고요청
    def _opt50027(self, rqname, trcode):
        myhave_rows = self._get_repeat_cnt(trcode, rqname)
        for i in range(myhave_rows):
            code = self._comm_get_data(trcode, "", rqname, i, "종목코드")
            item_name = self._comm_get_data(trcode, "", rqname, i, "종목명")
            myhave_cnt = self._comm_get_data(trcode, "", rqname, i, "보유수량")
            sell_or_buy = self._comm_get_data(trcode, "", rqname, i, "매매구분")

            if myhave_cnt != '0':
                self.option_myhave['code'].append(str(code))
                self.option_myhave['myhave_cnt'].append(abs(int(myhave_cnt)))
                self.option_myhave['sell_or_buy'].append(abs(int(sell_or_buy)))

    # 예탁금및증거금조회
    def _opw20010(self, rqname, trcode):
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

    # 선옵계좌별주문가능수량요청
    def _opw20009(self, rqname, trcode):
        new_order_able_cnt = self._comm_get_data(trcode, "", rqname, '0', "신규가능수량")
        order_able_cash = self._comm_get_data(trcode, "", rqname, '0', "주문가능현금")

        # 신규가능수량
        self.future_s_option_s_new_order_able_cnt = abs(int(new_order_able_cnt))
        # print(self.future_s_option_s_new_order_able_cnt)
        # 주문가능현금
        self.order_able_cash = abs(int(order_able_cash))
        # print(self.order_able_cash)

    # 체결강도조회
    def _optkwfid(self, rqname, trcode):
        deal_power_rows = self._get_repeat_cnt(trcode, rqname)
        # multi data
        for i in range(deal_power_rows):
            stock_no = self._comm_get_data(trcode, "", rqname, i, "종목코드")
            stock_name = self._comm_get_data(trcode, "", rqname, i, "종목명")
            run_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            sell_price = self._comm_get_data(trcode, "", rqname, i, "매도호가")
            sell_cnt = self._comm_get_data(trcode, "", rqname, i, "우선매도잔량")
            buy_price = self._comm_get_data(trcode, "", rqname, i, "매수호가")
            buy_cnt = self._comm_get_data(trcode, "", rqname, i, "우선매수잔량")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "거래량")
            deal_power = self._comm_get_data(trcode, "", rqname, i, "체결강도")

            # if deal_power_rows == len(self.favorites_item_list):
            if stock_no == self.favorites_item_list[i]:
                self.deal_power_data['stock_no'].append(str(stock_no))
                self.deal_power_data['stock_name'].append(str(stock_name))

                self.deal_power_data['run_price'].append(abs(int(run_price)))
                self.deal_power_data['sell_price'].append(abs(int(sell_price)))
                self.deal_power_data['sell_cnt'].append(abs(int(sell_cnt)))
                self.deal_power_data['buy_price'].append(abs(int(buy_price)))
                self.deal_power_data['buy_cnt'].append(abs(int(buy_cnt)))
                self.deal_power_data['vol_cnt'].append(abs(int(vol_cnt)))
                self.deal_power_data['deal_power'].append(abs(float(deal_power)))

            # if deal_power_rows == len(self.stock_have_data['stock_no']):
            #     if stock_no == self.stock_have_data['stock_no'][i]:
            #         self.stock_have_data['run_price'][i] = (abs(int(run_price)))
            #
            #         self.stock_have_data['sell_price'][i] = (abs(int(sell_price)))
            #         self.stock_have_data['sell_cnt'][i] = (abs(int(sell_cnt)))
            #         self.stock_have_data['buy_price'][i] = (abs(int(buy_price)))
            #         self.stock_have_data['buy_cnt'][i] = (abs(int(buy_cnt)))
            #         self.stock_have_data['vol_cnt'][i] = (abs(int(vol_cnt)))
            #
            #         self.stock_have_data['deal_power'][i] = (abs(float(deal_power)))

    # 선물월차트요청
    def _opt50072(self, rqname, trcode):
        future_s_shlc_month_data_rows = self._get_repeat_cnt(trcode, rqname)
        # multi data
        for i in range(future_s_shlc_month_data_rows):
            future_s_date = self._comm_get_data(trcode, "", rqname, i, "일자")
            future_s_start = self._comm_get_data(trcode, "", rqname, i, "시가")
            future_s_high = self._comm_get_data(trcode, "", rqname, i, "고가")
            future_s_low = self._comm_get_data(trcode, "", rqname, i, "저가")
            future_s_end = self._comm_get_data(trcode, "", rqname, i, "현재가")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "누적거래량")

            self.output_future_s_chain_shlc_month_data['future_s_date'].append(str(future_s_date[:8]))
            self.output_future_s_chain_shlc_month_data['future_s_start'].append(abs(float(future_s_start)))
            self.output_future_s_chain_shlc_month_data['future_s_high'].append(abs(float(future_s_high)))
            self.output_future_s_chain_shlc_month_data['future_s_low'].append(abs(float(future_s_low)))
            self.output_future_s_chain_shlc_month_data['future_s_end'].append(abs(float(future_s_end)))
            self.output_future_s_chain_shlc_month_data['vol_cnt'].append(abs(int(vol_cnt)))

    # 선물옵션일차트요청
    def _OPT50030(self, rqname, trcode):
        future_s_shlc_day_data_rows = self._get_repeat_cnt(trcode, rqname)
        # multi data
        for i in range(future_s_shlc_day_data_rows):
            future_s_date = self._comm_get_data(trcode, "", rqname, i, "일자")
            future_s_start = self._comm_get_data(trcode, "", rqname, i, "시가")
            future_s_high = self._comm_get_data(trcode, "", rqname, i, "고가")
            future_s_low = self._comm_get_data(trcode, "", rqname, i, "저가")
            future_s_end = self._comm_get_data(trcode, "", rqname, i, "현재가")

            self.output_future_s_chain_shlc_day_data['future_s_date'].append(str(future_s_date))
            self.output_future_s_chain_shlc_day_data['future_s_start'].append(abs(float(future_s_start)))
            self.output_future_s_chain_shlc_day_data['future_s_high'].append(abs(float(future_s_high)))
            self.output_future_s_chain_shlc_day_data['future_s_low'].append(abs(float(future_s_low)))
            self.output_future_s_chain_shlc_day_data['future_s_end'].append(abs(float(future_s_end)))

    # 주식월봉차트조회요청
    def _opt10083(self, rqname, trcode):
        stock_shlc_month_data_rows = self._get_repeat_cnt(trcode, rqname)
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
        # multi data
        for i in range(stock_shlc_data_rows):
            stock_date = self._comm_get_data(trcode, "", rqname, i, "일자")
            stock_start = self._comm_get_data(trcode, "", rqname, i, "시가")
            stock_high = self._comm_get_data(trcode, "", rqname, i, "고가")
            stock_low = self._comm_get_data(trcode, "", rqname, i, "저가")
            stock_end = self._comm_get_data(trcode, "", rqname, i, "현재가")
            vol_cnt = self._comm_get_data(trcode, "", rqname, i, "거래량")

            self.output_stock_shlc_data['stock_date'].append(str(stock_date))
            self.output_stock_shlc_data['stock_start'].append(abs(int(stock_start)))
            self.output_stock_shlc_data['stock_high'].append(abs(int(stock_high)))
            self.output_stock_shlc_data['stock_low'].append(abs(int(stock_low)))
            self.output_stock_shlc_data['stock_end'].append(abs(int(stock_end)))
            self.output_stock_shlc_data['vol_cnt'].append(abs(int(vol_cnt)))

    # stock
    # TR을 통해 얻어온 데이터를 인스턴스 변수 초기화
    def stock_shlc_month_reset_output(self):
        self.output_stock_shlc_month_data = {'stock_date': [], 'stock_start': [], 'stock_high': [], 'stock_low': [],
                                        'stock_end': [], 'vol_cnt': []}
    def stock_shlc_reset_output(self):
        self.output_stock_shlc_data = {'stock_date': [], 'stock_start': [], 'stock_high': [], 'stock_low': [],
                                        'stock_end': [], 'vol_cnt': []}

    # futrue_s 선물
    # TR을 통해 얻어온 데이터를 인스턴스 변수 초기화
    def future_s_chain_shlc_month_reset_output(self):
        self.output_future_s_chain_shlc_month_data = {'future_s_date': [], 'future_s_start': [], 'future_s_high': [],
                                                      'future_s_low': [], 'future_s_end': [], 'vol_cnt': []}
    def future_s_chain_shlc_day_reset_output(self):
        self.output_future_s_chain_shlc_day_data = {'future_s_date': [], 'future_s_start': [], 'future_s_high': [],
                                                      'future_s_low': [], 'future_s_end': [], 'vol_cnt': []}
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
        self.option_s_sell_deposit_money_data = {'call_adj_price': [], 'call_max_price': [], 'call_yesday_price': [], 'call_sell_order_deposit_money': [],
                                        'option_price': [], 'put_sell_order_deposit_money': [], 'put_yesday_price': [], 'put_max_price': [],
                                        'put_adj_price': []}

    # stock
    # TR을 통해 얻어온 데이터를 인스턴스 변수에 저장
    def stock_deal_power_reset_output(self):
        self.deal_power_data = {'stock_no': [], 'stock_name': [], 'run_price': [], 'sell_price': [], 'sell_cnt': [],
                                'buy_price': [], 'buy_cnt': [], 'vol_cnt': [], 'deal_power': []}
    def stock_have_data_reset_output(self):
        self.stock_have_data = {'stock_no': [], 'stock_name': [], 'market_in_price': [], 'myhave_cnt': [],
                                'run_price': [], 'sell_price': [], 'sell_cnt': [], 'buy_price': [], 'buy_cnt': [],
                                'vol_cnt': [], 'deal_power': []}

# 이벤트 슬롯
    # 선물전체시세요청 - 이벤트 슬롯
    def futrue_s_data_rq(self):
        # 인스턴스 변수 선언
        self.futrue_s_reset_output()

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
        self.server_set_rq_future_s_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)
        print('선물전체시세요청 전송')

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
        self.server_set_rq_future_s_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)
        print('선물전체시세요청 전송_차월물')

        # 서버에서 수신받은 콜 풋 데이터
        print('# 서버에서 수신받은 선물전체시세 데이터')
        print(self.futrue_s_data)
        # 차월물
        print(self.futrue_s_data_45)

        # 영업일 기준 잔존일
        future_s_day_residue_int = self.futrue_s_data['day_residue'][0]
        self.future_s_day_residue_str = str(future_s_day_residue_int)
        print(self.future_s_day_residue_str)
        future_s_45_day_residue_int = self.futrue_s_data_45['day_residue'][0]
        self.future_s_45_day_residue_str = str(future_s_45_day_residue_int)
        print(self.future_s_45_day_residue_str)


    # 콜/풋 월별시세요청 - 이벤트 슬롯
    def call_put_data_rq(self):
        # 인스턴스 변수 선언
        self.option_reset_output()

        # 콜종목결제월별시세요청
        sID = "만기년월"
        sValue = self.kiwoom.get_month_mall(0)
        self.current_monthmall_var = sValue
        sRQName = "콜종목결제월별시세요청"
        sTrCode = "OPT50021"
        nPrevNext = 0
        sScreenNo = "0021"
        # 서버요청
        self.server_set_rq_call_put_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)
        print('콜종목결제월별시세요청 전송')

        # 풋종목결제월별시세요청
        sID = "만기년월"
        sValue = self.kiwoom.get_month_mall(0)
        self.current_monthmall_var = sValue
        sRQName = "풋종목결제월별시세요청"
        sTrCode = "OPT50022"
        nPrevNext = 0
        sScreenNo = "0022"
        # 서버요청
        self.server_set_rq_call_put_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)
        print('풋종목결제월별시세요청 전송')

        # 중심가 함수 호출
        center_index_option_price = self.center_option_price_fn(self.option_price_rows,
                                                                self.output_call_option_data, self.output_put_option_data)
        self.center_index = center_index_option_price[1]
        self.center_option_price = center_index_option_price[2]
        if self.center_index != 0:
            # 비교변수 초기 바인딩(slow)
            self.slow_cmp_var_reset()
        # 장시작 최초 center_index == 0 경우 예측
        # 차월물 중심가 인덱스 존재하고 중심가가 같을때 실행함(차월물과 당월물의 차이가 비슷할때)
        elif self.center_index == 0:
            print('elif self.center_index == 0:')
            # GetOptionATM() 함수 호출
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
                    self.center_option_price = option_price_float
                    self.center_index = i

                    # 비교변수 초기 바인딩(slow)
                    self.slow_cmp_var_reset()

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
        self.server_set_rq_call_put_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)
        print('콜종목결제월별시세요청_45 전송')

        # 풋종목결제월별시세요청_45
        sID = "만기년월"
        sValue = self.kiwoom.get_month_mall(1)
        # self.current_monthmall_var = sValue
        sRQName = "풋종목결제월별시세요청_45"
        sTrCode = "OPT50022"
        nPrevNext = 0
        sScreenNo = "0022"
        # 서버요청
        self.server_set_rq_call_put_data(sID, sValue, sRQName, sTrCode, nPrevNext, sScreenNo)
        print('풋종목결제월별시세요청_45 전송')

        # 중심가(45) 함수(차월물) :: 당월물의 중심가와 같은 차월물 인텍스를 찾음
        center_index_option_price_45 = self.center_option_price_45_fn(self.center_option_price,
                                                                   self.output_call_option_data_45, self.output_put_option_data_45)
        self.center_index_45 = center_index_option_price_45[1]
        self.center_option_price_45 = center_index_option_price_45[2]

        # 서버에서 수신받은 콜 풋 데이터
        print('# 서버에서 수신받은 콜 풋 데이터')
        print(self.output_call_option_data)
        print(self.output_put_option_data)
        # 차월물
        print(self.output_call_option_data_45)
        print(self.output_put_option_data_45)

        # 중심가 중심인덱스
        print('# 중심가 중심인덱스')
        print(center_index_option_price[0])
        print(self.center_index)
        print(self.center_option_price)
        # 차월물
        print('# 차월물 중심가 중심인덱스')
        print(center_index_option_price_45[0])
        print(self.center_index_45)
        print(self.center_option_price_45)

        # 장시작 최초 center_index == 0 경우 예측
        # 차월물 중심가 인덱스 존재하고 중심가가 같을때 실행함(차월물과 당월물의 차이가 비슷할때)
        if (self.center_index == 0) or (self.center_index_45 == 0):
            # or (self.center_option_price != self.center_option_price_45):
            print('if (self.center_index == 0) or (self.center_index_45 == 0):')
            # GetOptionATM() 함수 호출
            option_s_atm_str = self.kiwoom.get_option_s_atm()
            # print(option_s_atm_str)
            # print(type(option_s_atm_str))
            # 콜옵션 자료와 비교
            for i in range(len(self.output_call_option_data_45['code'])):
                option_price_float = float(self.output_call_option_data_45['option_price'][i])
                option_price_float_mul_int = int(option_price_float * 100)
                option_price_float_mul_int_str = str(option_price_float_mul_int)
                # print(option_price_float_mul_int_str)
                # print(type(option_price_float_mul_int_str))
                if option_s_atm_str == option_price_float_mul_int_str:
                    self.center_option_price_45 = option_price_float
                    self.center_index_45 = i

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
        self.server_set_rq_DayResidue(sID1, sValue1, sID2, sValue2, sRQName, sTrCode, nPrevNext, sScreenNo)
        print('선옵잔존일조회요청 전송')

        # 영업일 기준 잔존일
        day_residue_int = self.output_put_option_data['day_residue'][self.center_index]
        self.day_residue_str = str(day_residue_int)

        # 콜/풋 월별시세요청 완료 - 1초 타이머 재시작
        self.timer1.start(1000)
        self.printt('콜/풋 월별시세요청 완료 timer1 시작')

    # 옵션매도주문증거금 요청
    def option_s_sell_deposit_money_data_rq(self):
        # 영업일 기준 잔존일
        day_residue_int = self.output_put_option_data['day_residue'][self.center_index]
        # [ opw20015 : 옵션매도주문증거금 ]
        if day_residue_int > 2:
            # option_s_sell_deposit_money_data
            # 인스턴스 변수 선언
            self.option_s_sell_deposit_money_output()
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
            print('옵션매도주문증거금 전송')
            self.server_set_rq_option_s_sell_deposit_money_data(sID1, sValue1, sID2, sValue2, sRQName, sTrCode,
                                                                nPrevNext, sScreenNo)
        else:
            # option_s_sell_deposit_money_data
            # 인스턴스 변수 선언
            self.option_s_sell_deposit_money_output()
            # 당월물
            sID1 = "월물구분"
            sValue1 = self.kiwoom.get_month_mall(1)
            sID2 = "클래스구분"
            sValue2 = "01"
            sRQName = "옵션매도주문증거금"
            sTrCode = "opw20015"
            nPrevNext = "0"
            sScreenNo = "20015"
            # 서버요청
            print('옵션매도주문증거금 전송')
            self.server_set_rq_option_s_sell_deposit_money_data(sID1, sValue1, sID2, sValue2, sRQName, sTrCode,
                                                                nPrevNext, sScreenNo)
        # print('# 서버에서 수신받은 옵션매도주문증거금')
        # print(self.option_s_sell_deposit_money_data)

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
        self.printt('업종별주가요청 전송')

    # 계좌평가잔고내역요청 - 이벤트 슬롯
    def stock_have_data_rq(self):
        # 인스턴스 변수 선언
        self.stock_have_data_reset_output()

        # 계좌평가잔고내역요청
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
        self.server_set_rq_stock_have_data(sID1, sValue1, sID2, sValue2, sID3, sValue3, sID4, sValue4, sRQName, sTrCode,
                                           nPrevNext, sScreenNo)
        # 연속조회시
        while self.remained_data == True:
            nPrevNext = 2
            # 서버요청
            self.server_set_rq_stock_have_data(sID1, sValue1, sID2, sValue2, sID3, sValue3, sID4, sValue4, sRQName, sTrCode,
                                           nPrevNext, sScreenNo)
        self.printt('계좌평가잔고내역요청 전송')

        # # 체결강도조회 - 이벤트 슬롯 - 관심종목 조회함수 활용(거래량, 매도호가, 매수호가, 체결강도)
        # transCode = ''
        # transCode_cnt = 0
        # for code in self.stock_have_data['stock_no']:
        #     # print(code)
        #     transCode = transCode + code + ';'
        #     transCode_cnt += 1
        # # self.printt(transCode)
        # # self.printt(transCode_cnt)
        # self.deal_power_trans_fn(transCode, transCode_cnt)

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
        self.comm_kw_rq_data(sArrCode, bNext, nCodeCount, nTypeFlag, sRQName, sScreenNo)
        # print('체결강도조회 전송')

    # 선물월차트요청
    def future_s_shlc_month_data_fn(self, future_s_code, current_today):
        # 인스턴스 변수 선언
        self.future_s_chain_shlc_month_reset_output()

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
        self.server_set_rq_future_s_shlc_month_data(sID1, sValue1, sID2, sValue2, sRQName,
                                                 sTrCode, nPrevNext, sScreenNo)
        # print('선물월차트요청 전송')

    # 선물옵션일차트요청
    def future_s_shlc_day_data_fn(self, future_s_code, current_today):
        # 인스턴스 변수 선언
        self.future_s_chain_shlc_day_reset_output()

        # 선물옵션일차트요청
        sID1 = "종목코드"
        sValue1 = future_s_code
        # sID2 = "기준일자"
        # sValue2 = current_today
        sRQName = "선물옵션일차트요청"
        sTrCode = "OPT50030"
        nPrevNext = "0"
        sScreenNo = "50030"
        # 서버요청
        self.server_set_rq_future_s_shlc_day_data(sID1, sValue1, sRQName,
                                                 sTrCode, nPrevNext, sScreenNo)
        # print('선물옵션일차트요청 전송')

    # 주식월봉차트조회요청
    def stock_shlc_month_data_fn(self, stock_code, ref_day, end_day):
        # 인스턴스 변수 선언
        self.stock_shlc_month_reset_output()

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
        self.server_set_rq_stock_shlc_month_data(sID1, sValue1, sID2, sValue2, sID3, sValue3, sID4, sValue4, sRQName,
                                                 sTrCode, nPrevNext, sScreenNo)
        # print('주식월봉차트조회요청 전송')

    # 주식일봉차트조회요청
    def stock_shlc_data_fn(self, stock_code, current_today):
        # 인스턴스 변수 선언
        self.stock_shlc_reset_output()

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
        self.server_set_rq_stock_shlc_data(sID1, sValue1, sID2, sValue2, sID3, sValue3, sRQName, sTrCode, nPrevNext, sScreenNo)
        # print('주식일봉차트조회요청 전송')

    # 선옵잔고요청 변수선언
    # 주문시 선옵잔고 변수 초기화
    def reset_myhave_var(self):
        self.option_myhave = {'code': [], 'myhave_cnt': [], 'sell_or_buy': []}

    # 선옵잔고요청 - 이벤트 슬롯
    def myhave_option_rq(self):
        # 선옵잔고요청 변수선언
        # 주문시 선옵잔고 변수 초기화
        self.reset_myhave_var()

        # 선옵잔고요청
        sID = "계좌번호"
        accountrunVar = self.comboBox_acc.currentText()
        sRQName = "선옵잔고요청"
        sTrCode = "OPT50027"
        nPrevNext = 0
        sScreenNo = "50027"
        # 서버요청
        self.server_set_rq_MyHave(sID, accountrunVar, sRQName, sTrCode, nPrevNext, sScreenNo)
        self.printt(self.option_myhave)

        # 버튼에 표기
        self.pushButton_fu_buy_have.setStyleSheet('background-color: rgb(255, 255, 255)')
        # 클릭 불가능
        self.pushButton_fu_buy_have.setEnabled(False)
        # 버튼에 표기
        self.pushButton_fu_sell_have.setStyleSheet('background-color: rgb(255, 255, 255)')
        # 클릭 불가능
        self.pushButton_fu_sell_have.setEnabled(False)
        # 버튼에 표기
        self.pushButton_callhave.setStyleSheet('background-color: rgb(255, 255, 255)')
        # 클릭 불가능
        self.pushButton_callhave.setEnabled(False)
        # 버튼에 표기
        self.pushButton_puthave.setStyleSheet('background-color: rgb(255, 255, 255)')
        # 클릭 불가능
        self.pushButton_puthave.setEnabled(False)
        for i in range(len(self.option_myhave['code'])):
            # print(self.option_myhave['code'][i][:3])
            if self.option_myhave['code'][i][:3] == '101':
                if self.option_myhave['sell_or_buy'][i] == 2:
                    self.pushButton_fu_buy_have.setStyleSheet('background-color: rgb(255, 0, 0)')
                    self.pushButton_fu_buy_have.setText(self.option_myhave['code'][i])
                    # 클릭 가능
                    self.pushButton_fu_buy_have.setEnabled(True)
                elif self.option_myhave['sell_or_buy'][i] == 1:
                    self.pushButton_fu_sell_have.setStyleSheet('background-color: rgb(0, 0, 255)')
                    self.pushButton_fu_sell_have.setText(self.option_myhave['code'][i])
                    # 클릭 가능
                    self.pushButton_fu_sell_have.setEnabled(True)
            elif self.option_myhave['code'][i][:3] == '201':
                if self.option_myhave['sell_or_buy'][i] == 2:
                    self.pushButton_callhave.setStyleSheet('background-color: rgb(255, 0, 0)')
                    # 클릭 가능
                    self.pushButton_callhave.setEnabled(True)
                elif self.option_myhave['sell_or_buy'][i] == 1:
                    self.pushButton_callhave.setStyleSheet('background-color: rgb(255, 0, 0)')
                    # 클릭 가능
                    self.pushButton_callhave.setEnabled(True)
            elif self.option_myhave['code'][i][:3] == '301':
                if self.option_myhave['sell_or_buy'][i] == 2:
                    self.pushButton_puthave.setStyleSheet('background-color: rgb(0, 0, 255)')
                    # 클릭 가능
                    self.pushButton_puthave.setEnabled(True)
                elif self.option_myhave['sell_or_buy'][i] == 1:
                    self.pushButton_puthave.setStyleSheet('background-color: rgb(0, 0, 255)')
                    # 클릭 가능
                    self.pushButton_puthave.setEnabled(True)
        # 예탁금및증거금조회 - 이벤트 슬롯
        self.mymoney_option_rq()

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
        # 신규가능수량
        print('self.future_s_option_s_new_order_able_cnt')
        print(self.future_s_option_s_new_order_able_cnt)

    # 예탁금및증거금조회 - 이벤트 슬롯
    def mymoney_option_rq(self):
        # 변수선언
        self.option_mymoney = {'deposit_money': [], 'margin_call': [], 'order_able': [], 'total_money': []}
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
        self.server_set_rq_OptionMoney(sID1, accountrunVar, sID2, sValue2, sID3, sValue3, sRQName, sTrCode, nPrevNext, sScreenNo)
        print(self.option_mymoney)

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
        self.server_set_rq_future_s_option_s_order_able_cnt(sID1, accountrunVar, sID2, sValue2, sID3, sValue3,
                                                            sID4, sValue4, sID5, sValue5, sID6, sValue6, sID7, sValue7,
                                                            sRQName, sTrCode, nPrevNext, sScreenNo)

    # 테스트
    def test(self):

        # 시간표시
        current_time = datetime.datetime.now()
        # print(current_time)
        # print(current_time.time())
        # index_text_time = current_time.toString('hh:mm')
        store_time_var = current_time.time()
        # current_time = time.ctime()




        # 중심가 변경시
        self.printt('# 중심가 변경시 옵션 튜닝 준비 = > 항상 현재에 맞춰서 <= 롤오버에도 활용')
        self.option_s_center_index_change_ready()











































    # 장마감 c_to_cf_hand
    def c_to_cf_hand(self):
        # 장마감 c 이후

        # API에서 지난 월봉(30개월)간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
        # API에서 지난 30일간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
        # 폴더명용
        current_year = datetime.datetime.today().strftime("%Y")
        current_today = datetime.datetime.today().strftime("%Y%m%d")

        # 텍스트파일명용stock_trend_line_of_ai_month_able
        choice_stock_filename = 'k95_max_of_kodex100'
        # db명 설정(월봉 / 일봉)
        db_name_db_month = Folder_Name_DB_Store + '/' + '/' + 'k95_max_stock_shlc_data_month' + '.db'
        db_name_db_day = Folder_Name_DB_Store + '/' + '/' + 'k95_max_stock_shlc_data_day' + '.db'
        # print(db_name_db_month)
        # print(db_name_db_day)
        self.stock_shlc_store_for_ai_fn(current_today, choice_stock_filename, db_name_db_month, db_name_db_day)

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

        # AI trend_line
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store

        # k95_max
        # db명 설정
        get_db_name = 'k95_max_stock_shlc_data_month' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_month' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 30
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

        # db명 설정
        get_db_name = 'k95_max_stock_shlc_data_day' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_day' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 60
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

        # 관리종목
        # db명 설정
        get_db_name = 'favorites_stock_shlc_data_month' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_month' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 30
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

        # db명 설정
        get_db_name = 'favorites_stock_shlc_data_day' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_day' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 60
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

        # 연결선물
        # db명 설정
        get_db_name = 'future_s_shlc_data_month' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_month' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 30
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

        # db명 설정
        get_db_name = 'future_s_shlc_data_day' + '.db'
        # db명 설정
        put_db_name = 'stock_trend_line_of_ai_day' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 60
        stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

        # 일봉 시뮬레이션 저장
        # db명 설정
        get_db_name = 'future_s_shlc_data_day' + '.db'
        # db명 설정
        put_db_name = 'future_s_simul_of_trend_line_day' + '.db'
        # 봉갯수
        stock_price_candle_cnt = 60
        future_s_simul_of_trend_line_day_store(current_today, db_file_path, get_db_name, put_db_name,
                                               stock_price_candle_cnt)

        # 선택종목 crawling 이후 장마감 변수 클리어
        self.MarketEndingVar = 'cf'
        self.printt('self.MarketEndingVar = cf')

    # 자동주문 클릭시 - 이벤트 슬롯
    def auto_order_button(self):
        if self.auto_order_button_var == False:
            self.auto_order_button_var = True
            self.printt(self.auto_order_button_var)
            self.pushButton_auto_order.setStyleSheet('background-color: rgb(255, 0, 0)')
            # 계좌선택 못하게
            self.comboBox_acc.setEnabled(False)
            self.comboBox_acc_stock.setEnabled(False)

            # 계좌잔고 시세요청
            self.stock_have_data_rq()
            # # 테이블 위젯에 표시하기
            # self.stock_listed_slot(self.stock_have_data)
            # 서버에서 수신받은 stock_data
            self.printt('# 서버에서 수신받은 stock_data')
            self.printt(len(self.stock_have_data['stock_no']))
            self.printt(self.stock_have_data)

            # 선옵잔고요청 - 이벤트 슬롯
            self.myhave_option_rq()
            # # 예탁금및증거금조회 - 이벤트 슬롯
            # self.mymoney_option_rq()

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
        # 마지막에 바인딩되는 output_put_option_data 영업일기준만료일이 모두 채워졌을때부터 실시간 시작
        if len(self.output_put_option_data_45['deal_power']) != 0:
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
        sell_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 27)
        buy_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 28)
        vol_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 13)

        # print(sRealType)
        # print(strCode)
        # print(run_price)

        for i in range(len(self.stock_have_data['stock_no'])):
            if strCode == self.stock_have_data['stock_no'][i]:
                self.stock_have_data['run_price'][i] = (abs(int(run_price)))
                self.stock_have_data['sell_price'][i] = (abs(int(sell_price)))
                self.stock_have_data['buy_price'][i] = (abs(int(buy_price)))
                self.stock_have_data['vol_cnt'][i] = (abs(int(vol_cnt)))

    # 주식체결
    def _real_time_stock_deal_ok(self, strCode, sRealType):
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        run_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 10)
        sell_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 27)
        buy_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 28)
        vol_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 13)
        deal_power = self.kiwoom.dynamicCall("GetCommRealData(QString, float)", strCode, 228)

        # print(sRealType)
        # print(strCode)
        # print(run_price)

        for i in range(len(self.stock_have_data['stock_no'])):
            if strCode == self.stock_have_data['stock_no'][i]:
                self.stock_have_data['run_price'][i] = (abs(int(run_price)))
                self.stock_have_data['sell_price'][i] = (abs(int(sell_price)))
                self.stock_have_data['buy_price'][i] = (abs(int(buy_price)))
                self.stock_have_data['vol_cnt'][i] = (abs(int(vol_cnt)))
                self.stock_have_data['deal_power'][i] = (abs(float(deal_power)))

                # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
                if self.MarketEndingVar == '3':
                    # 선물 변화 건수 체크
                    future_s_change_cnt = len(self.future_s_change_listed_var)
                    if future_s_change_cnt >= 2:
                        # 자동주문 버튼 True 주문실행
                        if self.auto_order_button_var == True:
                            # 선물변화 프로세스 실행중 여부
                            if self.future_s_change_running == False:
                                # 주식매도 종목검색
                                self.stock_sell_items_search(strCode, self.stock_have_data)

    # 주식우선호가
    def _real_time_stock_price_sellbuy(self, strCode, sRealType):
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        sell_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 27)
        buy_price = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 28)

        # print(sRealType)
        # print(strCode)
        # print(sell_price)
        # print(buy_price)

        for i in range(len(self.stock_have_data['stock_no'])):
            if strCode == self.stock_have_data['stock_no'][i]:
                self.stock_have_data['sell_price'][i] = (abs(int(sell_price)))
                self.stock_have_data['buy_price'][i] = (abs(int(buy_price)))

    # 주식호가잔량
    def _real_time_stock_price_cnt(self, strCode, sRealType):
        # (현재가 - 10, 매도호가 27, 매도호가수량 61, 매수호가 28, 매수호가수량 71)
        sell_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 61)
        buy_cnt = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 71)

        for i in range(len(self.stock_have_data['stock_no'])):
            if strCode == self.stock_have_data['stock_no'][i]:
                self.stock_have_data['sell_cnt'][i] = (abs(int(sell_cnt)))
                self.stock_have_data['buy_cnt'][i] = (abs(int(buy_cnt)))

    # elif (sRealType == "장시작시간"):
    def _real_time_endding_market(self, strCode, sRealType):
        self.MarketEndingVar = self.kiwoom.dynamicCall("GetCommRealData(QString, int)", strCode, 215)

        # 텍스트로 처리함
        # MarketEndingVar_int = abs(int(self.MarketEndingVar))
        # 장시작시간(215: 장운영구분(0:장시작전, 2: 장종료전, 3: 장시작, 4, 8: 장종료, 9: 장마감)
        if self.MarketEndingVar == '2':
            # self.printt(self.MarketEndingVar)
            # self.printt('장마감 2')    # 15:20:01(1분간격 정도로 반복)
            # # 시간표시
            # current_time = time.ctime()
            # self.printt(current_time)
            pass

        elif self.MarketEndingVar == '3':
            self.printt(self.MarketEndingVar)
            self.printt('장시작 알림 3')
            # # 콜/풋 월별시세요청 전 - 1초 타이머 중지
            # self.timer1.stop()
            # self.printt('timer1 콜/풋 월별시세요청 전 타이머 중지')
            # # 콜/풋 월별시세요청
            # self.printt('장시작 콜/풋 월별시세요청')
            # self.call_put_data_rq()
            if self.center_index != 0:
                # 비교변수 초기 바인딩(slow)
                self.slow_cmp_var_reset()
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

        elif self.MarketEndingVar == 'c':
            self.printt(self.MarketEndingVar)
            self.printt('장마감 c')    # 16:00:01
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
        # 자동주문 아닐때는(수동 주문일때)는 패스
        if self.auto_order_button_var == False:
            return

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

                    # 주문 실행 결과로
                    self.order_run_result(order_run_result_var)

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

                    # 주문 실행 결과로
                    self.order_run_result_stock(order_run_result_var)

            # 체결
            elif OrderRunKind == "체결":
                # 주문상태 / 매수도구분/ 종목코드 / 주문수량 / 주문가격 / 원 주문번호
                SellBuyType = self.get_chejan_data(907)
                OrderRunCode = self.get_chejan_data(9001)
                OrderRunCode_A = self.get_chejan_data(9001)
                OrderDealOk_cnt = self.get_chejan_data(911)
                OrderDealOk_price = self.get_chejan_data(910)
                OrgOrderNo = self.get_chejan_data(9203)

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

                        # 주문 실행 결과로
                        self.order_run_result(order_run_result_var)

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

                        # 주문 실행 결과로
                        self.order_run_result_stock(order_run_result_var)

        # 특이신호
        # else:
        #     print(gubun)
        #     print("구분 : 특이신호")

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
        # 선옵잔고요청 변수선언
        # 주문시 선옵잔고 변수 초기화
        self.reset_myhave_var()

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
                # 주문 실행 결과로
                self.order_run_result(order_run_result_var)
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
        # 선옵잔고요청 - 이벤트 슬롯
        self.myhave_option_rq()

        # # 진행바 표시(주문중)
        # self.progressBar_order.setValue(0)
        # # 체결완료 정정 타이머 중지
        # self.timer60.stop()
        # self.printt('체결완료 정정 타이머 중지')

        # 주문 타이머 중지
        self.timer_order.stop()
        self.printt('주문 타이머 중지')

        # # 체결완료 1초 타이머 재시작
        # self.timer1.start(1000)
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





    # 다음 중심가 변경시 까지 체결 않된건 취소하기
    def cancel_order(self, cancel_order_items):
        self.printt('다음 중심가 변경시 까지 체결 않된건 취소하기')
        # 시간표시
        current_time = time.ctime()
        self.printt(current_time)
        self.printt(cancel_order_items)

        # 주문할 때 필요한 계좌 정보를 QComboBox 위젯으로부터
        accountrunVar = self.comboBox_acc.currentText()
        # "거래구분"(1:지정가, 2:조건부지정가, 3:시장가, 4:최유리지정가, 5:지정가IOC, 6:지정가FOK, 7:시장가IOC, 8:시장가FOK, 9:최유리IOC, A: 최유리FOK)
        sOrdTp = '1'
        # 주문 순차적으로 동시실행
        for i in range(len(cancel_order_items['OrderRunCode'])):
            sRQName = cancel_order_items['OrderRunCode'][i]
            sScreenNo = (i + 3001)
            #  "주문유형"(1:신규매매, 2:정정, 3:취소)
            IOrdKind = 3
            # "매매구분"(1:매도, 2:매수)
            sslbyTp = cancel_order_items['SellBuyType'][i]
            # "주문수량"
            cancel_item_cnt = cancel_order_items['OrderRunVolume'][i]
            # "주문가격"
            Price = cancel_order_items['OrderRunPrice'][i]
            # "원주문번호"
            sOrgOrdNo_cell = cancel_order_items['OrgOrderNo'][i]
            # 종목코드
            CodeCallPut = cancel_order_items['OrderRunCode'][i]

            self.printt('취소 주문 실행 여부')
            self.printt(CodeCallPut[:3])

            # 신규주문과 달리 취소 주문은 사전 종목검색 별도 없으므로 현재의 주문종목 코드가 [선물/콜/옵션] 일때만 주문실행
            if CodeCallPut[:3] in ['201', '301']:    # 주문 취소시 선물주문 취소는 예외(선물 옵션 정정주문 예외시)20240104
                # 선물옵션 주문명령
                # SendOrderFO("사용자구분요청명", "화면번호", "계좌번호", "종목코드", "주문유형"(1:신규매매, 2:정정, 3:취소),
                # "매매구분"(1:매도, 2:매수),
                # "거래구분"(1:지정가, 2:조건부지정가, 3:시장가, 4:최유리지정가, 5:지정가IOC, 6:지정가FOK, 7:시장가IOC, 8:시장가FOK, 9:최유리IOC, A: 최유리FOK),
                # "주문수량", "주문가격", "원주문번호")
                send_order_result_var = self.kiwoom.send_order(sRQName, sScreenNo, accountrunVar, CodeCallPut, IOrdKind, sslbyTp, sOrdTp, cancel_item_cnt, Price, sOrgOrdNo_cell)

                # 주문 전송결과 성공일때
                if send_order_result_var == 0:
                    self.printt('취소 전송성공')
                    self.printt(send_order_result_var)
                else:
                    self.printt('전송실패')
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
    def order_ready_stock(self, cross_winner, volume_listed_var, item_list, sOrgOrdNo, stock_have_data):
        # 주문 종목 인텍스 찾기
        order_index = []
        order_cross_winner = []
        order_volume = []
        order_item = []
        order_sOrgOrdNo = []
        for i in range(len(stock_have_data['stock_no'])):
            for j in range(len(item_list)):
                if stock_have_data['stock_no'][i] == item_list[j]:
                    order_index.append(i)
                    order_cross_winner.append(cross_winner[j])
                    order_volume.append(volume_listed_var[j])
                    order_item.append(item_list[j])
                    order_sOrgOrdNo.append(sOrgOrdNo[j])

        self.printt(order_index)
        self.printt(order_item)
        self.printt(order_volume)

        # 주문할 때 필요한 계좌 정보를 QComboBox 위젯으로부터
        accountrunVar = self.comboBox_acc_stock.currentText()
        # "거래구분"(00 : 지정가  /  03 : 시장가)
        sHogaGb = '00'
        # 주문 순차적으로 동시실행
        for i in range(len(order_item)):
            # 서버요청 쉬어감
            time.sleep(TR_REQ_TIME_INTERVAL)

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
                PriceSellBuy = 'run_price'
                # "주문가격"
                Price = stock_have_data[PriceSellBuy][order_index[i]]
                # "원주문번호"
                sOrgOrdNo_cell = order_sOrgOrdNo[i]

            # 매도
            elif order_cross_winner[i] == 7004:
                #  "주문유형"(주문유형 1:신규매수, 2:신규매도 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정)
                IOrdKind = 2
                # "매매구분"(1:매도, 2:매수)
                sslbyTp = 1
                # "주문가격"
                PriceSellBuy = 'run_price'
                # "주문가격"
                Price = stock_have_data[PriceSellBuy][order_index[i]]
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

                # 주문 실행 결과로
                self.order_run_result_stock(order_run_result_var)

            else:
                self.printt('전송실패')
                self.printt(send_order_result_var)

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
                # # 타이머 중지  ## stock option 동시주문시 stock에 의해서 self.timer1.start(1000) 않됨
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

        # 계좌잔고 시세요청
        self.stock_have_data_rq()
        # # 테이블 위젯에 표시하기
        # self.stock_listed_slot(self.stock_have_data)
        # 서버에서 수신받은 stock_data
        self.printt('# 서버에서 수신받은 stock_data')
        self.printt(len(self.stock_have_data['stock_no']))
        self.printt(self.stock_have_data)

        # 주문타이머 중지
        self.timer_order_stock.stop()
        self.printt('stock 주문타이머 중지')
        # # 타이머 시작
        # self.timer1.start(1000)
        # self.printt('stock 주문체결완료 timer1 재시작')

    # 주식매도 종목검색
    def stock_sell_items_search(self, strCode, stock_have_data):
        sell_item_list = []
        for i in range(len(stock_have_data['stock_no'])):
            # 종목코드 같을때
            if stock_have_data['stock_no'][i] == strCode:
                # 재고있을때
                if stock_have_data['myhave_cnt'][i] > 0:
                    # 전송중이면 통과
                    if strCode in self.order_trans_var_stock['OrderRunCode']:
                        continue
                    # 접수목록에 있으면 통과
                    elif strCode in self.order_input_var_stock['OrderRunCode']:
                        continue
                    # 지금의 매도목록에 있으면 통과
                    elif strCode in sell_item_list:
                        continue
                    # 오늘 매도목록에 있으면 통과
                    elif strCode in self.selled_today_items:
                        continue
                    else:
                        # 매도건수 체크
                        market_out_cnt = self.tarket_earn_cnt_fn(strCode, stock_have_data)
                        # 매도건수 0이상이면
                        if market_out_cnt > 0:
                            sell_item_list.append(strCode)
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            self.printt('-----')
                            self.printt('매도종목검색 실행시간 : ' + text_time)
                            self.printt('sell_item_list.append(strCode)')
                            self.printt(strCode)
                            self.printt('market_in_price / run_price')
                            self.printt(format(stock_have_data['market_in_price'][i], ','))
                            self.printt(format(stock_have_data['run_price'][i], ','))
                            self.printt('market_out_cnt')
                            self.printt(market_out_cnt)

        if len(sell_item_list) != 0:
            cross_winner = []
            volume_listed_var = []
            item_list = []
            sOrgOrdNo = []
            self.printt('목표수익 도달 청산')
            cross_winner_cell = 7004
            self.printt(cross_winner_cell)
            sOrgOrdNo_cell = ''
            for i in range(len(stock_have_data['stock_no'])):
                for have in range(len(sell_item_list)):
                    if stock_have_data['stock_no'][i] == sell_item_list[have]:
                        if stock_have_data['myhave_cnt'][i] > 0:
                            cross_winner.append(cross_winner_cell)
                            volume_listed_var.append(market_out_cnt)
                            item_list.append(sell_item_list[have])
                            sOrgOrdNo.append(sOrgOrdNo_cell)
            self.printt(item_list)

            # 자동주문 버튼 True 주문실행
            if self.auto_order_button_var == True:
                # 주문준비 완료
                self.order_ready_stock(cross_winner, volume_listed_var, item_list, sOrgOrdNo, stock_have_data)

    # 목표건수 구하기(tarket_earn_cnt_fn)
    def tarket_earn_cnt_fn(self, strCode, stock_have_data):
        #  ai로 구한값 매도처리
        if self.stock_trend_line_of_ai_day != None:
            for i in range(len(self.stock_trend_line_of_ai_day['stock_no'])):
                for k in range(len(stock_have_data['stock_no'])):
                    if stock_have_data['stock_no'][k] == strCode:
                        if self.stock_trend_line_of_ai_day['stock_no'][i] == stock_have_data['stock_no'][k]:
                            each_run_price = stock_have_data['run_price'][k]
                            each_sell_max_price = self.stock_trend_line_of_ai_day['poly_sell_max_price'][i]
                            if each_sell_max_price <= each_run_price:
                                # 모든조건 만족 매도건수 구하기
                                sell_market_out_cnt = (self.market_in_percent_won * 1.1) / stock_have_data['run_price'][k]
                                sell_market_out_cnt_int = int(sell_market_out_cnt)
                                # 매도가능 건수
                                # # 만일 3차원 기울기가 하나라도 (-)이면 모두 청산 :: 2021년 01월 19일 수정
                                # if ((self.stock_trend_line_of_ai_day['poly_h_gradient'][i] < 0) or (
                                #         self.stock_trend_line_of_ai_day['poly_l_gradient'][i] < 0)):
                                #     return stock_have_data['myhave_cnt'][k]
                                if sell_market_out_cnt_int >= stock_have_data['myhave_cnt'][k]:
                                    return stock_have_data['myhave_cnt'][k]
                                elif sell_market_out_cnt_int == 0:
                                    sell_market_out_cnt_int = 0
                                    # self.printt('sell_market_out_cnt_int = 0')
                                    # self.printt(sell_market_out_cnt_int)
                                    return sell_market_out_cnt_int
                                elif sell_market_out_cnt_int > 0:
                                    # self.printt('buy_market_in_cnt')
                                    # self.printt(buy_market_in_cnt)
                                    # self.printt(buy_market_in_cnt_int)
                                    return sell_market_out_cnt_int

        return 0

    # 주식매수 종목검색
    def stock_buy_items_search(self, deal_power_tarket_item_list, deal_power_data, buyed_today_items):
        buy_item_list = []
        # 매수종목 추가시 가능금액 차감
        buy_able_money = self.buy_able_money
        for i in range(len(deal_power_tarket_item_list)):
            for j in range(len(deal_power_data['stock_no'])):
                # 종목코드 같을때
                if deal_power_tarket_item_list[i] == deal_power_data['stock_no'][j]:
                    # 전송중이면 통과
                    if deal_power_tarket_item_list[i] in self.order_trans_var_stock['OrderRunCode']:
                        continue
                    # 접수목록에 있으면 통과
                    elif deal_power_tarket_item_list[i] in self.order_input_var_stock['OrderRunCode']:
                        continue
                    # 지금의 매수목록에 있으면 통과
                    elif deal_power_tarket_item_list[i] in buy_item_list:
                        continue
                    # 오늘 매수목록에 있으면 통과
                    elif deal_power_tarket_item_list[i] in buyed_today_items:
                        continue
                    else:
                        # 매수건수 체크
                        market_in_cnt = self.market_in_buy_cnt(deal_power_tarket_item_list[i], deal_power_data,
                                                               buy_able_money)
                        # 매수건수 0이상이면
                        if market_in_cnt > 0:
                            # 매수종목 추가시 가능금액 차감
                            buy_able_money = buy_able_money - self.market_in_percent_won

                            buy_item_list.append(deal_power_tarket_item_list[i])

        # 매수종목 추가시 가능금액 차감
        buy_able_money = self.buy_able_money
        if len(buy_item_list) != 0:
            cross_winner = []
            volume_listed_var = []
            item_list = []
            sOrgOrdNo = []
            self.printt('체결강도 기준초과 진입')
            cross_winner_cell = 1004
            self.printt(cross_winner_cell)
            sOrgOrdNo_cell = ''
            for have in range(len(buy_item_list)):
                for i in range(len(deal_power_data['stock_no'])):
                    if buy_item_list[have] == deal_power_data['stock_no'][i]:
                        # 매수건수 체크
                        market_in_cnt = self.market_in_buy_cnt(buy_item_list[have], deal_power_data,
                                                               buy_able_money)
                        # 매수건수 0이상이면
                        if market_in_cnt > 0:
                            # 매수종목 추가시 가능금액 차감
                            buy_able_money = buy_able_money - self.market_in_percent_won

                            cross_winner.append(cross_winner_cell)
                            volume_listed_var.append(market_in_cnt)
                            item_list.append(buy_item_list[have])
                            sOrgOrdNo.append(sOrgOrdNo_cell)
            self.printt(item_list)

            # 자동주문 버튼 True 주문실행
            if self.auto_order_button_var == True:
                # 주문준비 완료
                self.order_ready_stock(cross_winner, volume_listed_var, item_list, sOrgOrdNo, deal_power_data)

    # 매수 건수 체크
    def market_in_buy_cnt(self, buy_item_list, deal_power_data, buy_able_money):
        for i in range(len(deal_power_data['stock_no'])):
            if buy_item_list == deal_power_data['stock_no'][i]:
                # 주문가능 금액 < self.market_in_percent_won
                if buy_able_money < self.market_in_percent_won:
                    buy_market_in_cnt_int = 0
                    self.printt('buy_able_money < self.market_in_percent_won')
                    self.printt(buy_market_in_cnt_int)
                    return buy_market_in_cnt_int
                else:
                    buy_market_in_cnt = self.market_in_percent_won / deal_power_data['run_price'][i]
                    buy_market_in_cnt_int = int(buy_market_in_cnt)
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
        self.printt('slow_cross_check_var')
        self.printt(slow_cross_check_var)

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

                # 중심가 함수 호출
                center_index_option_price = self.center_option_price_fn(self.option_price_rows,
                                                                        self.output_call_option_data,
                                                                        self.output_put_option_data)
                self.center_index = center_index_option_price[1]
                self.center_option_price = center_index_option_price[2]

                # 중심가(45) 함수(차월물) :: 당월물의 중심가와 같은 차월물 인텍스를 찾음
                center_index_option_price_45 = self.center_option_price_45_fn(self.center_option_price,
                                                                              self.output_call_option_data_45,
                                                                              self.output_put_option_data_45)
                self.center_index_45 = center_index_option_price_45[1]
                self.center_option_price_45 = center_index_option_price_45[2]

                # 중심가 중심인덱스
                self.printt('# 중심가 중심인덱스')
                self.printt(center_index_option_price[0])
                self.printt(self.center_index)
                self.printt(self.center_option_price)
                # 차월물
                self.printt('# 차월물 중심가 중심인덱스')
                self.printt(center_index_option_price_45[0])
                self.printt(self.center_index_45)
                self.printt(self.center_option_price_45)

                if self.center_index != 0:
                    # 비교변수 초기 바인딩(slow)
                    self.slow_cmp_var_reset()

                # 중심가 변경시
                self.printt('# 중심가 변경시 옵션 튜닝 준비 = > 항상 현재에 맞춰서 <= 롤오버에도 활용')
                self.option_s_center_index_change_ready()

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

                # 중심가 함수 호출
                center_index_option_price = self.center_option_price_fn(self.option_price_rows,
                                                                        self.output_call_option_data,
                                                                        self.output_put_option_data)
                self.center_index = center_index_option_price[1]
                self.center_option_price = center_index_option_price[2]

                # 중심가(45) 함수(차월물) :: 당월물의 중심가와 같은 차월물 인텍스를 찾음
                center_index_option_price_45 = self.center_option_price_45_fn(self.center_option_price,
                                                                              self.output_call_option_data_45,
                                                                              self.output_put_option_data_45)
                self.center_index_45 = center_index_option_price_45[1]
                self.center_option_price_45 = center_index_option_price_45[2]

                # 중심가 중심인덱스
                self.printt('# 중심가 중심인덱스')
                self.printt(center_index_option_price[0])
                self.printt(self.center_index)
                self.printt(self.center_option_price)
                # 차월물
                self.printt('# 차월물 중심가 중심인덱스')
                self.printt(center_index_option_price_45[0])
                self.printt(self.center_index_45)
                self.printt(self.center_option_price_45)

                if self.center_index != 0:
                    # 비교변수 초기 바인딩(slow)
                    self.slow_cmp_var_reset()

                # 중심가 변경시
                self.printt('# 중심가 변경시 옵션 튜닝 준비 = > 항상 현재에 맞춰서 <= 롤오버에도 활용')
                self.option_s_center_index_change_ready()

    # money_option_point_ch
    def money_option_point_ch(self, money_won):
        money_point = money_won / Option_Mul_Money
        return money_point

    # 옵션 종목검색
    def option_items_search(self, option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt):
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': [], 'point': []}
        self.pushButton_call_item_list.setText('')
        self.pushButton_put_item_list.setText('')
        option_items_search_max_space = 1.25    # +25%
        option_items_search_min_space = 0.75    # -25%

        # 옵션 매도 최대금액
        # 선물옵션 순자산금액 + stock 추정예탁자산
        option_have_money_plus_estimated_deposit = self.option_have_money + self.estimated_deposit
        # print(option_have_money_plus_estimated_deposit)
        # 바스켓으로 먼저 나눠주고
        option_have_money_plus_estimated_deposit_basket_cnt_remove = option_have_money_plus_estimated_deposit / basket_cnt
        # print(option_have_money_plus_estimated_deposit_basket_cnt_remove)
        # (선옵 순자산 + stock 추정예탁자산) /  Future_s_Leverage_Int * 2
        option_s_sell_onetime_max_money = option_have_money_plus_estimated_deposit_basket_cnt_remove / Future_s_Leverage_Int * 2
        # print(option_s_sell_onetime_max_money)
        self.printt('option_s_sell_onetime_max_money')
        self.printt(option_s_sell_onetime_max_money)

        # 선물매도(풋매도 헷징)
        # put
        if put_or_call == 'put':
            if month_mall_type == 'center_index':
                # 당월물
                # self.center_index
                # 'Delta'
                option_s_delta = abs(self.output_put_option_data['Delta'][self.center_index + 1])
                # print(option_s_delta)
                option_s_delta_change = 100 / option_s_delta
                # print(option_s_delta_change)
                option_s_sell_buy_point_plus_delta = option_s_sell_buy_point * option_s_delta_change
                # print(option_s_sell_buy_point_plus_delta)
                self.printt('option_s_delta')
                self.printt(option_s_delta)
                self.printt('option_s_delta_change')
                self.printt(option_s_delta_change)
                self.printt('option_s_sell_buy_point_plus_delta')
                self.printt(option_s_sell_buy_point_plus_delta)

                # 옵션 행사가와 비교하여 옵션매도주문증거금 구하기
                for d in range(len(self.option_s_sell_deposit_money_data['option_price'])):
                    if self.option_s_sell_deposit_money_data['option_price'][d] == \
                            self.output_put_option_data['option_price'][self.center_index + 1]:
                        # 옵션매도주문증거금
                        self.option_s_sell_order_deposit_money = \
                        self.option_s_sell_deposit_money_data['put_sell_order_deposit_money'][d]
                        # print(self.option_s_sell_order_deposit_money)
                        self.printt('self.option_s_sell_order_deposit_money')
                        self.printt(self.option_s_sell_order_deposit_money)
                # 옵션 최대 건수 구하기(Option_Mul_Money = 250,000 활용)
                option_s_search_max_cnt = math.ceil(option_s_sell_onetime_max_money / self.option_s_sell_order_deposit_money)
                # print(option_s_search_max_cnt)
                self.printt('option_s_search_max_cnt')
                self.printt(option_s_search_max_cnt)

                # 현재가를 더하고 델타변환값과 비교하여 최대한(0.75~1.25) 옵션검색 완료
                option_comp_var = self.output_put_option_data['run_price'][self.center_index + 1]
                center_item_cnt = 1
                item_list_cnt['code_no'].append(self.output_put_option_data['code'][self.center_index + 1])
                item_list_cnt['cnt'].append(center_item_cnt)
                item_list_cnt['point'].append(self.output_put_option_data['run_price'][self.center_index + 1])
                for i in range(option_s_search_max_cnt):
                    if i == 0:
                        if option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_min_space):
                            break
                    else:
                        option_comp_var += self.output_put_option_data['run_price'][self.center_index + 1]
                        item_list_cnt['cnt'][0] += center_item_cnt
                        if option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_max_space):
                            item_list_cnt['cnt'][0] -= center_item_cnt
                            # item_list_cnt['code_no'].append(self.output_put_option_data['code'][self.center_index + 2])
                            # item_list_cnt['cnt'].append(center_item_cnt)
                            # item_list_cnt['point'].append(self.output_put_option_data['run_price'][self.center_index + 2])
                            break
                        elif option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_min_space):
                            break
            # 차월물
            elif month_mall_type == 'center_index_45':
                # 차월물
                # self.center_index_45
                # 'Delta'
                option_s_delta = abs(self.output_put_option_data_45['Delta'][self.center_index_45 + 1])
                # print(option_s_delta)
                option_s_delta_change = 100 / option_s_delta
                # print(option_s_delta_change)
                option_s_sell_buy_point_plus_delta = option_s_sell_buy_point * option_s_delta_change
                # print(option_s_sell_buy_point_plus_delta)
                self.printt('option_s_delta')
                self.printt(option_s_delta)
                self.printt('option_s_delta_change')
                self.printt(option_s_delta_change)
                self.printt('option_s_sell_buy_point_plus_delta')
                self.printt(option_s_sell_buy_point_plus_delta)

                # 옵션 행사가와 비교하여 옵션매도주문증거금 구하기
                for d in range(len(self.option_s_sell_deposit_money_data['option_price'])):
                    if self.option_s_sell_deposit_money_data['option_price'][d] == \
                            self.output_put_option_data_45['option_price'][self.center_index_45 + 1]:
                        # 옵션매도주문증거금
                        self.option_s_sell_order_deposit_money = \
                        self.option_s_sell_deposit_money_data['put_sell_order_deposit_money'][d]
                        # print(self.option_s_sell_order_deposit_money)
                        self.printt('self.option_s_sell_order_deposit_money')
                        self.printt(self.option_s_sell_order_deposit_money)
                # 옵션 최대 건수 구하기(Option_Mul_Money = 250,000 활용)
                option_s_search_max_cnt = math.ceil(option_s_sell_onetime_max_money / self.option_s_sell_order_deposit_money)
                # print(option_s_search_max_cnt)
                self.printt('option_s_search_max_cnt')
                self.printt(option_s_search_max_cnt)

                # 현재가를 더하고 델타변환값과 비교하여 최대한(0.75~1.25) 옵션검색 완료
                option_comp_var = self.output_put_option_data_45['run_price'][self.center_index_45 + 1]
                center_item_cnt = 1
                item_list_cnt['code_no'].append(self.output_put_option_data_45['code'][self.center_index_45 + 1])
                item_list_cnt['cnt'].append(center_item_cnt)
                item_list_cnt['point'].append(self.output_put_option_data_45['run_price'][self.center_index_45 + 1])
                for i in range(option_s_search_max_cnt):
                    if i == 0:
                        if option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_min_space):
                            break
                    else:
                        option_comp_var += self.output_put_option_data_45['run_price'][self.center_index_45 + 1]
                        item_list_cnt['cnt'][0] += center_item_cnt
                        if option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_max_space):
                            item_list_cnt['cnt'][0] -= center_item_cnt
                            # item_list_cnt['code_no'].append(self.output_put_option_data_45['code'][self.center_index_45 + 2])
                            # item_list_cnt['cnt'].append(center_item_cnt)
                            # item_list_cnt['point'].append(
                            #     self.output_put_option_data_45['run_price'][self.center_index_45 + 2])
                            break
                        elif option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_min_space):
                            break
            self.pushButton_put_item_list.setText(item_list_cnt['code_no'][-1])

        # 선물매수(콜매도 헷징)
        # call
        elif put_or_call == 'call':
            if month_mall_type == 'center_index':
                # 당월물
                # self.center_index
                # 'Delta'
                option_s_delta = abs(self.output_call_option_data['Delta'][self.center_index - 1])
                # print(option_s_delta)
                option_s_delta_change = 100 / option_s_delta
                # print(option_s_delta_change)
                option_s_sell_buy_point_plus_delta = option_s_sell_buy_point * option_s_delta_change
                # print(option_s_sell_buy_point_plus_delta)
                self.printt('option_s_delta')
                self.printt(option_s_delta)
                self.printt('option_s_delta_change')
                self.printt(option_s_delta_change)
                self.printt('option_s_sell_buy_point_plus_delta')
                self.printt(option_s_sell_buy_point_plus_delta)

                # 옵션 행사가와 비교하여 옵션매도주문증거금 구하기
                for d in range(len(self.option_s_sell_deposit_money_data['option_price'])):
                    if self.option_s_sell_deposit_money_data['option_price'][d] == \
                            self.output_call_option_data['option_price'][self.center_index - 1]:
                        # 옵션매도주문증거금
                        self.option_s_sell_order_deposit_money = \
                        self.option_s_sell_deposit_money_data['call_sell_order_deposit_money'][d]
                        # print(self.option_s_sell_order_deposit_money)
                        self.printt('self.option_s_sell_order_deposit_money')
                        self.printt(self.option_s_sell_order_deposit_money)
                # 옵션 최대 건수 구하기(Option_Mul_Money = 250,000 활용)
                option_s_search_max_cnt = math.ceil(option_s_sell_onetime_max_money / self.option_s_sell_order_deposit_money)
                # print(option_s_search_max_cnt)
                self.printt('option_s_search_max_cnt')
                self.printt(option_s_search_max_cnt)

                # 현재가를 더하고 델타변환값과 비교하여 최대한(0.75~1.25) 옵션검색 완료
                option_comp_var = self.output_call_option_data['run_price'][self.center_index - 1]
                center_item_cnt = 1
                item_list_cnt['code_no'].append(self.output_call_option_data['code'][self.center_index - 1])
                item_list_cnt['cnt'].append(center_item_cnt)
                item_list_cnt['point'].append(self.output_call_option_data['run_price'][self.center_index - 1])
                for i in range(option_s_search_max_cnt):
                    if i == 0:
                        if option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_min_space):
                            break
                    else:
                        option_comp_var += self.output_call_option_data['run_price'][self.center_index - 1]
                        item_list_cnt['cnt'][0] += center_item_cnt
                        if option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_max_space):
                            item_list_cnt['cnt'][0] -= center_item_cnt
                            # item_list_cnt['code_no'].append(self.output_call_option_data['code'][self.center_index - 2])
                            # item_list_cnt['cnt'].append(center_item_cnt)
                            # item_list_cnt['point'].append(self.output_call_option_data['run_price'][self.center_index - 2])
                            break
                        elif option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_min_space):
                            break
            # 차월물
            elif month_mall_type == 'center_index_45':
                # 차월물
                # self.center_index_45
                # 'Delta'
                option_s_delta = abs(self.output_call_option_data_45['Delta'][self.center_index_45 - 1])
                # print(option_s_delta)
                option_s_delta_change = 100 / option_s_delta
                # print(option_s_delta_change)
                option_s_sell_buy_point_plus_delta = option_s_sell_buy_point * option_s_delta_change
                # print(option_s_sell_buy_point_plus_delta)
                self.printt('option_s_delta')
                self.printt(option_s_delta)
                self.printt('option_s_delta_change')
                self.printt(option_s_delta_change)
                self.printt('option_s_sell_buy_point_plus_delta')
                self.printt(option_s_sell_buy_point_plus_delta)

                # 옵션 행사가와 비교하여 옵션매도주문증거금 구하기
                for d in range(len(self.option_s_sell_deposit_money_data['option_price'])):
                    if self.option_s_sell_deposit_money_data['option_price'][d] == \
                            self.output_call_option_data_45['option_price'][self.center_index_45 - 1]:
                        # 옵션매도주문증거금
                        self.option_s_sell_order_deposit_money = \
                        self.option_s_sell_deposit_money_data['call_sell_order_deposit_money'][d]
                        # print(self.option_s_sell_order_deposit_money)
                        self.printt('self.option_s_sell_order_deposit_money')
                        self.printt(self.option_s_sell_order_deposit_money)
                # 옵션 최대 건수 구하기(Option_Mul_Money = 250,000 활용)
                option_s_search_max_cnt = math.ceil(option_s_sell_onetime_max_money / self.option_s_sell_order_deposit_money)
                # print(option_s_search_max_cnt)
                self.printt('option_s_search_max_cnt')
                self.printt(option_s_search_max_cnt)

                # 현재가를 더하고 델타변환값과 비교하여 최대한(0.75~1.25) 옵션검색 완료
                option_comp_var = self.output_call_option_data_45['run_price'][self.center_index_45 - 1]
                center_item_cnt = 1
                item_list_cnt['code_no'].append(self.output_call_option_data_45['code'][self.center_index_45 - 1])
                item_list_cnt['cnt'].append(center_item_cnt)
                item_list_cnt['point'].append(self.output_call_option_data_45['run_price'][self.center_index_45 - 1])
                for i in range(option_s_search_max_cnt):
                    if i == 0:
                        if option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_min_space):
                            break
                    else:
                        option_comp_var += self.output_call_option_data_45['run_price'][self.center_index_45 - 1]
                        item_list_cnt['cnt'][0] += center_item_cnt
                        if option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_max_space):
                            item_list_cnt['cnt'][0] -= center_item_cnt
                            # item_list_cnt['code_no'].append(self.output_call_option_data_45['code'][self.center_index_45 - 2])
                            # item_list_cnt['cnt'].append(center_item_cnt)
                            # item_list_cnt['point'].append(
                            #     self.output_call_option_data_45['run_price'][self.center_index_45 - 2])
                            break
                        elif option_comp_var > (option_s_sell_buy_point_plus_delta * option_items_search_min_space):
                            break
            self.pushButton_call_item_list.setText(item_list_cnt['code_no'][-1])

        # print(item_list_cnt)
        return item_list_cnt

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

    # future_s_basket_cnt_text_store
    def future_s_basket_cnt_text_store(self, basket_cnt):
        # basket_cnt.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # basket_cnt  # int
        f = open(item_list_files_path + "future_s_basket_cnt_text.txt", 'wt', encoding='UTF8')
        store_data = str(basket_cnt)
        f.write(store_data)
        f.close()
    # future_s_basket_cnt_text_read
    def future_s_basket_cnt_text_read(self):
        # basket_cnt.txt 저장경로
        item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/'
        # basket_cnt  # int
        f = open(item_list_files_path + "future_s_basket_cnt_text.txt", 'rt', encoding='UTF8')
        basket_cnt_readlines = f.readlines()
        # print(basket_cnt_readlines)
        f.close()
        basket_cnt = int(basket_cnt_readlines[0])
        return basket_cnt

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
        # 봉갯수
        stock_price_candle_cnt = 30
        # 선물 현재가
        futrue_s_run_price = self.futrue_s_data['run_price'][0]
        futrue_s_start_price = self.futrue_s_data['start_price'][0]
        futrue_s_high_price = self.futrue_s_data['high_price'][0]
        futrue_s_low_price = self.futrue_s_data['low_price'][0]

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
            select_combobox = self.comboBox_future_s_chain_month.currentText()
            if select_combobox != '':
                # 선택시간 기준으로 데이타 수집
                # print(select_combobox)
                df_read_selected = df_read[df_read['stock_date'] <= select_combobox]
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

            # 차트 그리기
            self.draw_chart_future_s_chain(df_read_use, min_index, table_name, stock_price_candle_cnt, futrue_s_run_price, futrue_s_start_price, futrue_s_high_price, futrue_s_low_price)

        # db닫기
        con.commit()
        con.close()

    # 가저오기 함수::일봉(연결선물 차트그리기)
    def data_pickup_future_s_chain_day_select_fill(self):
        # AI trend_line
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # db명 설정
        get_db_name = 'future_s_shlc_data_day' + '.db'
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
            self.comboBox_future_s_chain_day.clear()
            self.comboBox_future_s_chain_day.addItems(date_str_labels)
            # 카운터
            combobox_future_s_chain_cnt = self.comboBox_future_s_chain_day.count()
            # print(combobox_future_s_chain_cnt)
            # 마지막 인텍스 선택
            if combobox_future_s_chain_cnt != 0:
                self.comboBox_future_s_chain_day.setCurrentIndex(combobox_future_s_chain_cnt - 1)

            self.data_pickup_future_s_chain_day()

        # db닫기
        con.commit()
        con.close()

    # 가저오기 함수::일봉(연결선물 차트그리기)
    def data_pickup_future_s_chain_day(self):
        # 봉갯수
        stock_price_candle_cnt = 60
        # 선물 현재가
        futrue_s_run_price = self.futrue_s_data['run_price'][0]
        futrue_s_start_price = self.futrue_s_data['start_price'][0]
        futrue_s_high_price = self.futrue_s_data['high_price'][0]
        futrue_s_low_price = self.futrue_s_data['low_price'][0]

        # AI trend_line
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        # db명 설정
        get_db_name = 'future_s_shlc_data_day' + '.db'
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
            select_combobox = self.comboBox_future_s_chain_day.currentText()
            if select_combobox != '':
                # 선택시간 기준으로 데이타 수집
                # print(select_combobox)
                df_read_selected = df_read[df_read['stock_date'] <= select_combobox]
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

            # 차트 그리기
            self.draw_chart_future_s_chain(df_read_use, min_index, table_name, stock_price_candle_cnt, futrue_s_run_price, futrue_s_start_price, futrue_s_high_price, futrue_s_low_price)

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

        # 부팅시 1회 실행::gui 하단에 표시
        # 월봉
        # 매도 기울기 상향중 체크
        stock_trend_line_of_ai_month_able = []
        stock_trend_line_of_ai_month_minuus = []
        stock_trend_line_of_ai_month_able_buy_able_item_code = []
        self.stock_trend_line_of_ai_month = self.stock_trend_line_of_ai_month_data_fn()
        if self.stock_trend_line_of_ai_month != None:
            for i in range(len(self.stock_trend_line_of_ai_month['stock_no'])):
                # 신규진입일때는 샹향중일때만 진입(월봉)
                if ((self.stock_trend_line_of_ai_month['poly_h_gradient'][i] > 0) and (
                        self.stock_trend_line_of_ai_month['poly_l_gradient'][i] > 0)):
                    if self.stock_trend_line_of_ai_month['stock_no'][i] not in stock_trend_line_of_ai_month_able:
                        stock_trend_line_of_ai_month_able.append(self.stock_trend_line_of_ai_month['stock_no'][i])
                elif ((self.stock_trend_line_of_ai_month['poly_h_gradient'][i] < 0) and (
                        self.stock_trend_line_of_ai_month['poly_l_gradient'][i] < 0)):
                    if self.stock_trend_line_of_ai_month['stock_no'][i] not in stock_trend_line_of_ai_month_minuus:
                        stock_trend_line_of_ai_month_minuus.append(self.stock_trend_line_of_ai_month['stock_no'][i])

                # 연결선물
                if Chain_Future_s_Item_Code[0] == self.stock_trend_line_of_ai_month['stock_no'][i]:
                    # gui 하단에 표시
                    self.future_s_chain_trend_line_of_ai_month_h_str = str(
                        format(self.stock_trend_line_of_ai_month['poly_h_gradient'][i], '.2f'))
                    self.future_s_chain_trend_line_of_ai_month_l_str = str(
                        format(self.stock_trend_line_of_ai_month['poly_l_gradient'][i], '.2f'))
            # gui 하단에 표시
            self.trend_line_of_ai_month_total_cnt_str = str(len(self.stock_trend_line_of_ai_month['stock_no']))
            self.trend_line_of_ai_month_plus_cnt_str = str(len(stock_trend_line_of_ai_month_able))
            self.trend_line_of_ai_month_minus_cnt_str = str(len(stock_trend_line_of_ai_month_minuus))

        self.stock_trend_line_of_ai_day = self.stock_trend_line_of_ai_day_data_fn()
        # self.printt('# self.stock_trend_line_of_ai_day')
        # self.printt(self.stock_trend_line_of_ai_day)
        # ai로 구한 값 있을때만 실행
        if self.stock_trend_line_of_ai_day != None:
            for i in range(len(self.stock_trend_line_of_ai_day['stock_no'])):
                # 연결선물
                if Chain_Future_s_Item_Code[0] == self.stock_trend_line_of_ai_day['stock_no'][i]:
                    # gui 하단에 표시
                    self.future_s_chain_trend_line_of_ai_day_h_str = str(format(self.stock_trend_line_of_ai_day['poly_h_gradient'][i], '.2f'))
                    self.future_s_chain_trend_line_of_ai_day_l_str = str(format(self.stock_trend_line_of_ai_day['poly_l_gradient'][i], '.2f'))
                    self.future_s_chain_day_poly_max_price_str = str(format(self.stock_trend_line_of_ai_day['poly_sell_max_price'][i], '.2f'))
                    self.future_s_chain_day_poly_min_price_str = str(format(self.stock_trend_line_of_ai_day['poly_buy_min_price'][i], '.2f'))

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

    # 선물변화 (0.1%이상)
    def future_s_change(self, future_s_percent_high, future_s_percent_low, futrue_s_data_run_price):
        # 선물지수 / K200 변화
        self.future_s_run.append(futrue_s_data_run_price)
        future_s_run_cnt = len(self.future_s_run)
        if future_s_run_cnt == 2:

            # 장중이며 선물변화 (0.1%이상)
            if ((self.future_s_run[-2] > (self.future_s_run[-1] * future_s_percent_high)) or (
                    self.future_s_run[-2] < (self.future_s_run[-1] * future_s_percent_low))):
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

    # 중심가 함수
    def center_option_price_fn(self, option_price_rows, call_data, put_data):
        # for i, data in enumerate(call_data['run_price']):
        center_call_index = 0
        center_call_option_price = ''
        center_put_index = 0
        center_put_option_price = ''
        center_index = 0
        center_option_price = 0
        for i in range(option_price_rows - 2):
            if (put_data['run_price'][i] > call_data['run_price'][i + 1]) and (call_data['run_price'][i + 1] > put_data['run_price'][i + 2]):
                # 위 아래 현재가가 제로일때는 다시
                if (put_data['run_price'][i] == 0) or (put_data['run_price'][i + 2] == 0):
                    continue
                center_call_index = i + 1
                center_call_option_price = call_data['option_price'][i + 1]
                # print(center_call_index)
                # print(center_call_option_price)

            if (call_data['run_price'][i] < put_data['run_price'][i + 1]) and (put_data['run_price'][i + 1] < call_data['run_price'][i + 2]):
                # 위 아래 현재가가 제로일때는 다시
                if (call_data['run_price'][i] == 0) or (call_data['run_price'][i + 2] == 0):
                    continue
                center_put_index = i + 1
                center_put_option_price = call_data['option_price'][i + 1]
                # print(center_put_index)
                # print(center_put_option_price)

        if (center_call_index == center_put_index) and (center_call_option_price == center_put_option_price) \
                and (center_call_index != 0) and (center_put_index != 0):
            center_index = center_call_index
            center_option_price = center_call_option_price

            return True, center_index, center_option_price

        else:

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
        # 영업일 기준 잔존일 건수가 0이 아닐때 실행
        if len(self.output_put_option_data['day_residue']) != 0:
            txt_file_store(Folder_Name_TXT_Store, self.Global_Option_Item_Code_var, self.day_residue_str,
                           store_data)
        else:
            print(store_data)

    # text_data_store_trans
    def printt_buyed(self, store_data):
        # 영업일 기준 잔존일 건수가 0이 아닐때 실행
        if len(self.output_put_option_data['day_residue']) != 0:
            txt_file_store(Folder_Name_TXT_Store, File_Kind_Buy, self.day_residue_str, store_data)
    # text_data_store_trans
    def printt_selled(self, store_data):
        # 영업일 기준 잔존일 건수가 0이 아닐때 실행
        if len(self.output_put_option_data['day_residue']) != 0:
            txt_file_store(Folder_Name_TXT_Store, File_Kind_Sell, self.day_residue_str, store_data)


    # 60초 한번씩 클럭 발생 :: 콜/풋 월별시세요청
    def timer_empty_fn(self):
        # 60초 한번씩 클럭 발생 :: 콜/풋 월별시세요청
        print('60초 경과 # 콜/풋 월별시세요청 실행')
        # 선물전체시세요청
        self.futrue_s_data_rq()
        # 콜/풋 월별시세요청
        self.call_put_data_rq()

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
            # # 중심가 생성 1초 타이머 재시작
            # self.timer1.start(1000)
            # self.printt('당월물 차월물 중심가 인덱스 생성 :: timer1 재시작')

    # 1초에 한번씩 클럭 발생
    def timer1sec(self):
        # stock / option 계좌선택
        # stock_accountrunVar
        stock_accountrunVar = self.comboBox_acc_stock.currentText()
        # option_accountrunVar
        option_accountrunVar = self.comboBox_acc.currentText()
        if stock_accountrunVar == option_accountrunVar:
            return
        # 계좌선택 이후 선옵잔고요청 가능
        self.pushButton_myhave.setEnabled(True)
        # 계좌선택 이후 자동주문 클릭 가능
        self.pushButton_auto_order.setEnabled(True)

        # 시분초 : db 중복 시분 제외 변수선언
        current_time = QTime.currentTime()
        db_overlap_time_except = current_time.toString('hh:mm')
        if db_overlap_time_except != self.db_overlap_time_list[-1]:
            # 선물변화 프로세스 실행중 여부
            self.future_s_change_running = True
            # 선물변화 (~%이상)
            future_s_change_ret = self.future_s_change(self.future_s_percent_high, self.future_s_percent_low, self.futrue_s_data['run_price'][0])
            if future_s_change_ret[0] == True:
                # True 인식과 동시에 저장함수 데이터 바인딩
                output_call_option_data = self.output_call_option_data
                output_put_option_data = self.output_put_option_data
                # 시간표시
                current_time = datetime.datetime.now()
                # print(current_time)
                # print(current_time.time())
                # index_text_time = current_time.toString('hh:mm')
                store_time_var = current_time.time()
                # current_time = time.ctime()

                self.printt('-----')
                self.printt(store_time_var)
                # 시분초 : db 중복 시분 제외 변수선언
                self.db_overlap_time_list.append(db_overlap_time_except)
                self.printt('self.db_overlap_time_list')
                self.printt(self.db_overlap_time_list)

                self.printt('future_s_change_ret')
                self.printt(future_s_change_ret)

                # slow 교차::선물변화시 center_index있으면 가장 먼저 실행해야함
                self.slow_cross_check_shift()
                # self.printt('self.slow_cmp_call + self.slow_cmp_put')
                # self.printt(self.slow_cmp_call)
                # self.printt(self.slow_cmp_put)
                # 교차체크전송 함수 호출
                self.slow_cross_check_trans()

                # 장시작 최초 center_index == 0 경우 예측
                # 차월물 중심가 인덱스 존재하고 중심가가 같을때 실행함(차월물과 당월물의 차이가 비슷할때)
                if (self.center_index == 0) or (self.center_index_45 == 0):
                    # or (self.center_option_price != self.center_option_price_45):
                    print('if (self.center_index == 0) or (self.center_index_45 == 0):')
                    # / 차월물 중심가 다름')
                    # 타이머 중지
                    self.timer1.stop()
                    print('timer1 타이머 중지')
                    # 60초 한번씩 클럭 발생 :: 콜/풋 월별시세요청
                    self.timer_empty.start(1000 * 60)
                    print('timer_empty 타이머 시작')
                    return

                # 선물 변화 건수 체크
                self.future_s_change_listed_var.append(future_s_change_ret[1])
                self.printt(self.future_s_change_listed_var)

                # # 선옵잔고요청 - 이벤트 슬롯
                # self.myhave_option_rq()
                # 선옵잔고요청 이후 틈새에 주식매도가 실행되어 리마킹      # 2019년 10월 29일 전략수정

                # 흐름변경 :: stock_delta / favorites_deal_power chart view
                # 저장함수
                self.data_store_ready(store_time_var, output_call_option_data, output_put_option_data)

                # 타이머 중지
                self.timer1.stop()
                self.printt('stock_buy_ready_fn 시작 timer1 중지')
                # 주식 매수 준비
                self.stock_buy_ready_fn(store_time_var)
                # 타이머 시작
                self.timer1.start(1000)
                self.printt('stock_buy_ready_fn 끝 timer1 재시작')

                # 옵션매도주문증거금 요청
                self.option_s_sell_deposit_money_data_rq()
                # 자동주문 버튼 True
                if self.auto_order_button_var == True:
                    # 선물 (진입/청산) 준비 및 옵션헤지
                    self.future_s_market_ready()

                # 옵션거래 [실시간 조회] 체크박스가 켜져있을때만
                if self.checkbox_realtime.isChecked():
                    # 선물 변화 건수 체크
                    future_s_change_cnt = len(self.future_s_change_listed_var)
                    if future_s_change_cnt >= 1:
                        # 가저오기 함수
                        self.data_pickup_1sec()
                # else:
                #     # 가저오기 함수(연결선물 차트그리기)
                #     self.data_pickup_future_s_chain_day()
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
        if future_s_change_cnt >= 1:
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

            # TREND LINE 정보
            trend_line_of_ai_month_text = 'TrendLine(M) ' + 'T(' + self.trend_line_of_ai_month_total_cnt_str + ')' +\
                                          ' ++(' + self.trend_line_of_ai_month_plus_cnt_str + ')' +\
                                          ' --(' + self.trend_line_of_ai_month_minus_cnt_str + ')'

            # 연결선물 정보
            future_s_chain_info_text = '연결선물 ' + 'M(' + self.future_s_chain_trend_line_of_ai_month_h_str + '/' + \
                                       self.future_s_chain_trend_line_of_ai_month_l_str + ')' + \
                                       ' D(' + self.future_s_chain_trend_line_of_ai_day_h_str + \
                                       '/' + self.future_s_chain_trend_line_of_ai_day_l_str + ')' + ' P(' + \
                                       self.future_s_chain_day_poly_max_price_str + '/' + \
                                       self.future_s_chain_day_poly_min_price_str + ')'
            # 선물
            future_s_run_text = '선물 ' + str(format(self.futrue_s_data['run_price'][0], '.2f'))

            self.statusbar.showMessage(self.accouns_id + '(' + self.accounts_name + ')' + ' | ' + state_msg +
                                       '(' + time_msg + ')' + ' | ' + future_s_run_text + ' | ' +
                                       future_s_chain_info_text + ' | ' + trend_line_of_ai_month_text + ' | ' +
                                       center_option_price_text + ' | ' + center_index_text + ' | ' +
                                       stock_have_cnt_view + ' | ' + day_residue_text + ' | ' +
                                       future_s_day_residue_text + ' | ' + MarketEndingVar_view)
        else:
            self.statusbar.showMessage(self.accouns_id + '(' + self.accounts_name + ')' + ' | ' +
                                       state_msg + '(' + time_msg + ')')

        # 선물 롤오버
        # 장마감 self.MarketEndingVar == '2'
        if self.MarketEndingVar == '2':
            # 장마감 2 이후
            # 선물 롤오버 1번실행
            self.future_s_roll_over_fn()

        # 장마감 self.MarketEndingVar == 'c' 각종 시세조회
        if self.MarketEndingVar == 'c':
            # 장마감 c 이후

            # API에서 지난 월봉(30개월)간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
            # API에서 지난 30일간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
            # 폴더명용
            current_year = datetime.datetime.today().strftime("%Y")
            current_today = datetime.datetime.today().strftime("%Y%m%d")

            # 텍스트파일명용stock_trend_line_of_ai_month_able
            choice_stock_filename = 'k95_max_of_kodex100'
            # db명 설정(월봉 / 일봉)
            db_name_db_month = Folder_Name_DB_Store + '/' + '/' + 'k95_max_stock_shlc_data_month' + '.db'
            db_name_db_day = Folder_Name_DB_Store + '/' + '/' + 'k95_max_stock_shlc_data_day' + '.db'
            # print(db_name_db_month)
            # print(db_name_db_day)
            self.stock_shlc_store_for_ai_fn(current_today, choice_stock_filename, db_name_db_month, db_name_db_day)

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

            # AI trend_line
            db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store

            # k95_max
            # db명 설정
            get_db_name = 'k95_max_stock_shlc_data_month' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_month' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 30
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

            # db명 설정
            get_db_name = 'k95_max_stock_shlc_data_day' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_day' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 60
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

            # 관리종목
            # db명 설정
            get_db_name = 'favorites_stock_shlc_data_month' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_month' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 30
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

            # db명 설정
            get_db_name = 'favorites_stock_shlc_data_day' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_day' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 60
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

            # 연결선물
            # db명 설정
            get_db_name = 'future_s_shlc_data_month' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_month' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 30
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

            # db명 설정
            get_db_name = 'future_s_shlc_data_day' + '.db'
            # db명 설정
            put_db_name = 'stock_trend_line_of_ai_day' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 60
            stock_trend_line_db_store(current_today, db_file_path, get_db_name, put_db_name, stock_price_candle_cnt)

            # 일봉 시뮬레이션 저장
            # db명 설정
            get_db_name = 'future_s_shlc_data_day' + '.db'
            # db명 설정
            put_db_name = 'future_s_simul_of_trend_line_day' + '.db'
            # 봉갯수
            stock_price_candle_cnt = 60
            future_s_simul_of_trend_line_day_store(current_today, db_file_path, get_db_name, put_db_name,
                                                   stock_price_candle_cnt)

            # 선택종목 crawling 이후 장마감 변수 클리어
            self.MarketEndingVar = 'cf'
            self.printt('self.MarketEndingVar = cf')

    # 중심가 변경시 옵션 튜닝 준비 = > 항상 현재에 맞춰서
    def option_s_center_index_change_ready(self):
        # # 중심가 중심인덱스 / # 차월물 중심가 중심인덱스 == 0 => return  ### 20230127 중심가 중심인덱스 0일경우에 실행되는 것을 방지하기 위하여~~
        if ((self.center_index == 0) or (self.center_index_45 == 0)):
            return

        # -----
        # 다음 중심가 변경시 까지 체결 않된건 취소하기
        # 취소 아이템 변수 선언
        cancel_order_items = {'OrderRunKind': [], 'SellBuyType': [], 'OrderRunCode': [], 'OrderRunVolume': [],
                                 'OrderRunPrice': [], 'OrgOrderNo': [], 'modify_item': []}
        # 체결 않된 아이템 건수(접수건수 - 체결건수)
        for i in range(len(self.order_input_var['OrderRunCode'])):
            for j in range(len(self.order_result_var['OrderRunCode'])):
                if self.order_input_var['OrderRunCode'][i] == self.order_result_var['OrderRunCode'][j]:
                    if self.order_input_var['OrderRunVolume'][i] > self.order_result_var['OrderRunVolume'][j]:
                        # 취소 아이템
                        cancel_order_items['OrderRunKind'].append(self.order_input_var['OrderRunKind'][i])
                        cancel_order_items['SellBuyType'].append(self.order_input_var['SellBuyType'][i])
                        cancel_order_items['OrderRunCode'].append(self.order_input_var['OrderRunCode'][i])
                        cancel_item_cnt = self.order_input_var['OrderRunVolume'][i] - \
                                          self.order_result_var['OrderRunVolume'][j]
                        cancel_order_items['OrderRunVolume'].append(cancel_item_cnt)
                        cancel_order_items['OrderRunPrice'].append(self.order_input_var['OrderRunPrice'][i])
                        cancel_order_items['OrgOrderNo'].append(self.order_input_var['OrgOrderNo'][i])
                        cancel_order_items['modify_item'].append('')
        # 취소 주문은 종목이 있을경우에만
        if len(cancel_order_items['OrderRunCode']) > 0:
            self.cancel_order(cancel_order_items)
        # -----

        # 초기화
        item_list_cnt_items_search = {'code_no': [], 'cnt': [], 'sell_buy_type': [], 'point': []}
        item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 선물 바스켓 가져오기
        basket_cnt = self.future_s_basket_cnt_text_read()   #int
        # print(basket_cnt)

        # 계좌잔고 시세요청
        self.stock_have_data_rq()
        # # 테이블 위젯에 표시하기
        # self.stock_listed_slot(self.stock_have_data)
        # 서버에서 수신받은 stock_data
        self.printt('# 서버에서 수신받은 stock_data')
        self.printt(len(self.stock_have_data['stock_no']))
        self.printt(self.stock_have_data)

        # 선옵잔고요청 - 이벤트 슬롯
        self.myhave_option_rq()
        # # 예탁금및증거금조회 - 이벤트 슬롯
        # self.mymoney_option_rq()
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

        # 선물 매도재고 => 풋청산(매수) 후 풋매도
        if myhave_sell_total_mall_basket_cnt_remove > 0:
            self.printt('선물 매도재고 있음')
            if myhave_sell_total_mall_basket_cnt_remove >= 4:
                # 당일 선물 진입여부 판단
                # 당일 거래 있었으면 텍스트 파일 호출 / 없었으면 시뮬레이터 계산
                if (self.futrue_s_data['item_code'][0] in self.selled_today_items) or (self.futrue_s_data_45['item_code'][0] in self.selled_today_items) or (Chain_Future_s_Item_Code[0] in self.selled_today_items):
                    # item_list.txt 저장경로
                    item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + 'today_put_order_lists.txt'
                    if os.path.exists(item_list_files_path):
                        os.remove(item_list_files_path)
                    # self.option_myhave = {'code': ['301SA307', '301SA310', '301SA315', '301SA317'],
                    #                       'myhave_cnt': [18, 15, 15, 3], 'sell_or_buy': [1, 1, 1, 1]}
                    # 301SA307::9::301SA310::15::301SA317::3::301SA315::5::
                    # 301SA307::9::301SA315::10::
                    # {'code_no': ['301SA307', '301SA315', '301SA310', '301SA317'], 'cnt': [18, 15, 15, 3], 'sell_buy_type': []}

                    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
                    future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
                    # self.printt('# future_s_simul_of_trend_line_day')
                    # self.printt(future_s_simul_of_trend_line_day)
                    for d in range(myhave_sell_total_mall_basket_cnt_remove - 2 - 1):
                        # 과거 시뮬레이션 값 가져와서 종목 찾기 & 주문할 종목코드 카운터 텍스트 저장
                        sell_mode_first = 0
                        sell_mode_cnt = 0
                        sell_ref_price = []
                        sell_second_price = []
                        # 시뮬레이터 구한 값 있을때만 실행
                        if future_s_simul_of_trend_line_day != None:
                            # sell_mode_cnt = 2
                            for i in range(len(future_s_simul_of_trend_line_day['deal_day'])):
                                # mode 더해보기(+-)
                                sell_mode_first += future_s_simul_of_trend_line_day['sell_mode'][i] - future_s_simul_of_trend_line_day['buy_mode'][i]
                                if sell_mode_first == (myhave_sell_total_mall_basket_cnt_remove - 2) - d:               # 역으로 today재고 저장
                                    sell_ref_price.append(future_s_simul_of_trend_line_day['poly_sell_max_price'][i])
                                    for j in range(i + 1, len(future_s_simul_of_trend_line_day['deal_day']) - 1):
                                        # mode 더해보기(+-)
                                        sell_mode_cnt += future_s_simul_of_trend_line_day['sell_mode'][
                                            j] - future_s_simul_of_trend_line_day['buy_mode'][j]
                                        if sell_mode_cnt == 2:
                                            sell_second_price.append(
                                                future_s_simul_of_trend_line_day['poly_sell_max_price'][j])
                                    break
                        # [315.06694648735436]
                        # print(sell_ref_price)
                        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
                        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
                        # print(sell_second_price)
                        # 지난진입 금액확인 :: 옵션매도 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(sell_ref_price[0] - sell_second_price[0])
                        option_s_point_sum += option_s_sell_buy_point
                        self.printt('sell_ref_price')
                        self.printt(sell_ref_price)
                        self.printt('sell_second_price')
                        self.printt(sell_second_price)
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)

                        # 옵션 종목검색()
                        put_or_call = 'put'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)

                        # if d == 0:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                        # else:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                        # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                        if d == 0:
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        else:
                            for i in range(len(item_list_cnt['code_no'])):
                                if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:                    # 첫번째 라인에서 저장한 코드와 동일할때
                                    for j in range(len(item_list_cnt_items_search['code_no'])):                             # 그 종목은 건수만 카운터 해주고
                                        if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:         # 그 종목이랑 동일할때
                                            item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                                else:
                                    item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                    item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        # print(item_list_cnt_items_search)

                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for s in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_put_order_list_text_store(item_list_cnt_for_store)

                    # option_s_sell_buy_point_text 가져오기
                    option_s_sell_buy_point_text_list = self.option_s_sell_buy_point_text_pickup()
                    # print(option_s_sell_buy_point_text_list)
                    option_s_sell_buy_point = option_s_sell_buy_point_text_list[-1]
                    # print(option_s_sell_buy_point)
                    option_s_point_sum += option_s_sell_buy_point
                    self.printt('option_s_sell_buy_point')
                    self.printt(option_s_sell_buy_point)

                    # 옵션 종목검색()
                    put_or_call = 'put'
                    if day_residue_int > 2:
                        month_mall_type = 'center_index'
                        # center_index / center_index_45
                    else:
                        month_mall_type = 'center_index_45'
                        # center_index / center_index_45
                    item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                    # print(item_list_cnt)

                    # if d == 0:
                    #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                    # else:
                    #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                    # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                    for i in range(len(item_list_cnt['code_no'])):
                        if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:  # 첫번째 라인에서 저장한 코드와 동일할때
                            for j in range(len(item_list_cnt_items_search['code_no'])):  # 그 종목은 건수만 카운터 해주고
                                if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:  # 그 종목이랑 동일할때
                                    item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                        else:
                            item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                            item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                            item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                    # print(item_list_cnt_items_search)

                    # 텍스트 저장은 종목이 있을경우에만
                    if len(item_list_cnt['code_no']) > 0:
                        item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                        for s in range(len(item_list_cnt['code_no'])):
                            item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                            item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                        # 종목코드와 수량(텍스트에 저장하기)
                        self.today_put_order_list_text_store(item_list_cnt_for_store)

                    # 검색결과 종목 vs option_myhave 비교하여 실제 거래항목 정하기
                    for s in range(len(item_list_cnt_items_search['code_no'])):
                        if item_list_cnt_items_search['code_no'][s] in self.option_myhave['code']:
                            for p in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][p] == item_list_cnt_items_search['code_no'][s]:
                                    # 재고가 혹시 매도
                                    if self.option_myhave['sell_or_buy'][p] == 1:
                                        if item_list_cnt_items_search['cnt'][s] > self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] - self.option_myhave['myhave_cnt'][p])
                                            item_list_cnt_type['sell_buy_type'].append(1)
                                        elif item_list_cnt_items_search['cnt'][s] < self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p] - item_list_cnt_items_search['cnt'][s])
                                            item_list_cnt_type['sell_buy_type'].append(2)
                                        elif item_list_cnt_items_search['cnt'][s] == self.option_myhave['myhave_cnt'][p]:
                                            pass
                                    # 재고가 행여나 매수
                                    elif self.option_myhave['sell_or_buy'][p] == 2:
                                        item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                        item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] + self.option_myhave['myhave_cnt'][p])
                                        item_list_cnt_type['sell_buy_type'].append(1)

                        else:
                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s])
                            item_list_cnt_type['sell_buy_type'].append(1)

                    # 만일 재고 항목이 검색항목에 없을때
                    for p in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][p] in item_list_cnt_items_search['code_no']:
                            pass
                        else:
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
                else:
                    # 당일 선물 진입여부 판단(없었을 경우)
                    # item_list.txt 저장경로
                    item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + 'today_put_order_lists.txt'
                    if os.path.exists(item_list_files_path):
                        os.remove(item_list_files_path)
                    # self.option_myhave = {'code': ['301SA307', '301SA310', '301SA315', '301SA317'],
                    #                       'myhave_cnt': [18, 15, 15, 3], 'sell_or_buy': [1, 1, 1, 1]}
                    # 301SA307::9::301SA310::15::301SA317::3::301SA315::5::
                    # 301SA307::9::301SA315::10::
                    # {'code_no': ['301SA307', '301SA315', '301SA310', '301SA317'], 'cnt': [18, 15, 15, 3], 'sell_buy_type': []}

                    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
                    future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
                    # self.printt('# future_s_simul_of_trend_line_day')
                    # self.printt(future_s_simul_of_trend_line_day)
                    for d in range(myhave_sell_total_mall_basket_cnt_remove - 2):
                        # 과거 시뮬레이션 값 가져와서 종목 찾기 & 주문할 종목코드 카운터 텍스트 저장
                        sell_mode_first = 0
                        sell_mode_cnt = 0
                        sell_ref_price = []
                        sell_second_price = []
                        # 시뮬레이터 구한 값 있을때만 실행
                        if future_s_simul_of_trend_line_day != None:
                            # sell_mode_cnt = 2
                            for i in range(len(future_s_simul_of_trend_line_day['deal_day'])):
                                # mode 더해보기(+-)
                                sell_mode_first += future_s_simul_of_trend_line_day['sell_mode'][i] - future_s_simul_of_trend_line_day['buy_mode'][i]
                                if sell_mode_first == (myhave_sell_total_mall_basket_cnt_remove - 2) - d:               # 역으로 today재고 저장
                                    sell_ref_price.append(future_s_simul_of_trend_line_day['poly_sell_max_price'][i])
                                    for j in range(i + 1, len(future_s_simul_of_trend_line_day['deal_day']) - 1):
                                        # mode 더해보기(+-)
                                        sell_mode_cnt += future_s_simul_of_trend_line_day['sell_mode'][
                                            j] - future_s_simul_of_trend_line_day['buy_mode'][j]
                                        if sell_mode_cnt == 2:
                                            sell_second_price.append(
                                                future_s_simul_of_trend_line_day['poly_sell_max_price'][j])
                                    break
                        # [315.06694648735436]
                        # print(sell_ref_price)
                        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
                        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
                        # print(sell_second_price)
                        # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(sell_ref_price[0] - sell_second_price[0])
                        option_s_point_sum += option_s_sell_buy_point
                        self.printt('sell_ref_price')
                        self.printt(sell_ref_price)
                        self.printt('sell_second_price')
                        self.printt(sell_second_price)
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)

                        # 옵션 종목검색()
                        put_or_call = 'put'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)

                        # if d == 0:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                        # else:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                        # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                        if d == 0:
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        else:
                            for i in range(len(item_list_cnt['code_no'])):
                                if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:                    # 첫번째 라인에서 저장한 코드와 동일할때
                                    for j in range(len(item_list_cnt_items_search['code_no'])):                             # 그 종목은 건수만 카운터 해주고
                                        if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:         # 그 종목이랑 동일할때
                                            item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                                else:
                                    item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                    item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        # print(item_list_cnt_items_search)

                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for s in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_put_order_list_text_store(item_list_cnt_for_store)

                    # 검색결과 종목 vs option_myhave 비교하여 실제 거래항목 정하기
                    for s in range(len(item_list_cnt_items_search['code_no'])):
                        if item_list_cnt_items_search['code_no'][s] in self.option_myhave['code']:
                            for p in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][p] == item_list_cnt_items_search['code_no'][s]:
                                    # 재고가 혹시 매도
                                    if self.option_myhave['sell_or_buy'][p] == 1:
                                        if item_list_cnt_items_search['cnt'][s] > self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] - self.option_myhave['myhave_cnt'][p])
                                            item_list_cnt_type['sell_buy_type'].append(1)
                                        elif item_list_cnt_items_search['cnt'][s] < self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p] - item_list_cnt_items_search['cnt'][s])
                                            item_list_cnt_type['sell_buy_type'].append(2)
                                        elif item_list_cnt_items_search['cnt'][s] == self.option_myhave['myhave_cnt'][p]:
                                            pass
                                    # 재고가 행여나 매수
                                    elif self.option_myhave['sell_or_buy'][p] == 2:
                                        item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                        item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] + self.option_myhave['myhave_cnt'][p])
                                        item_list_cnt_type['sell_buy_type'].append(1)

                        else:
                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s])
                            item_list_cnt_type['sell_buy_type'].append(1)

                    # 만일 재고 항목이 검색항목에 없을때
                    for p in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][p] in item_list_cnt_items_search['code_no']:
                            pass
                        else:
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
            # 선물 매도재고(3)
            elif myhave_sell_total_mall_basket_cnt_remove == 3:
                # 당일 선물 진입여부 판단
                # 당일 거래 있었으면 텍스트 파일 호출 / 없었으면 시뮬레이터 계산
                if (self.futrue_s_data['item_code'][0] in self.selled_today_items) or (self.futrue_s_data_45['item_code'][0] in self.selled_today_items) or (Chain_Future_s_Item_Code[0] in self.selled_today_items):
                    # item_list.txt 저장경로
                    item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + 'today_put_order_lists.txt'
                    if os.path.exists(item_list_files_path):
                        os.remove(item_list_files_path)
                    # self.option_myhave = {'code': ['301SA307', '301SA310', '301SA315', '301SA317'],
                    #                       'myhave_cnt': [18, 15, 15, 3], 'sell_or_buy': [1, 1, 1, 1]}
                    # 301SA307::9::301SA310::15::301SA317::3::301SA315::5::
                    # 301SA307::9::301SA315::10::
                    # {'code_no': ['301SA307', '301SA315', '301SA310', '301SA317'], 'cnt': [18, 15, 15, 3], 'sell_buy_type': []}

                    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
                    future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
                    # self.printt('# future_s_simul_of_trend_line_day')
                    # self.printt(future_s_simul_of_trend_line_day)
                    for d in range(myhave_sell_total_mall_basket_cnt_remove - 2 - 1):
                        # 과거 시뮬레이션 값 가져와서 종목 찾기 & 주문할 종목코드 카운터 텍스트 저장
                        sell_mode_first = 0
                        sell_mode_cnt = 0
                        sell_ref_price = []
                        sell_second_price = []
                        # 시뮬레이터 구한 값 있을때만 실행
                        if future_s_simul_of_trend_line_day != None:
                            # sell_mode_cnt = 2
                            for i in range(len(future_s_simul_of_trend_line_day['deal_day'])):
                                # mode 더해보기(+-)
                                sell_mode_first += future_s_simul_of_trend_line_day['sell_mode'][i] - future_s_simul_of_trend_line_day['buy_mode'][i]
                                if sell_mode_first == (myhave_sell_total_mall_basket_cnt_remove - 2) - d:               # 역으로 today재고 저장
                                    sell_ref_price.append(future_s_simul_of_trend_line_day['poly_sell_max_price'][i])
                                    for j in range(i + 1, len(future_s_simul_of_trend_line_day['deal_day']) - 1):
                                        # mode 더해보기(+-)
                                        sell_mode_cnt += future_s_simul_of_trend_line_day['sell_mode'][
                                            j] - future_s_simul_of_trend_line_day['buy_mode'][j]
                                        if sell_mode_cnt == 2:
                                            sell_second_price.append(
                                                future_s_simul_of_trend_line_day['poly_sell_max_price'][j])
                                    break
                        # [315.06694648735436]
                        # print(sell_ref_price)
                        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
                        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
                        # print(sell_second_price)
                        # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(sell_ref_price[0] - sell_second_price[0])
                        option_s_point_sum += option_s_sell_buy_point
                        self.printt('sell_ref_price')
                        self.printt(sell_ref_price)
                        self.printt('sell_second_price')
                        self.printt(sell_second_price)
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)

                        # 옵션 종목검색()
                        put_or_call = 'put'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)

                        # if d == 0:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                        # else:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                        # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                        if d == 0:
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        else:
                            for i in range(len(item_list_cnt['code_no'])):
                                if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:                    # 첫번째 라인에서 저장한 코드와 동일할때
                                    for j in range(len(item_list_cnt_items_search['code_no'])):                             # 그 종목은 건수만 카운터 해주고
                                        if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:         # 그 종목이랑 동일할때
                                            item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                                else:
                                    item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                    item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        # print(item_list_cnt_items_search)

                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for s in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_put_order_list_text_store(item_list_cnt_for_store)

                    # option_s_sell_buy_point_text 가져오기
                    option_s_sell_buy_point_text_list = self.option_s_sell_buy_point_text_pickup()
                    # print(option_s_sell_buy_point_text_list)
                    option_s_sell_buy_point = option_s_sell_buy_point_text_list[-1]
                    # print(option_s_sell_buy_point)
                    option_s_point_sum += option_s_sell_buy_point
                    self.printt('option_s_sell_buy_point')
                    self.printt(option_s_sell_buy_point)

                    # 옵션 종목검색()
                    put_or_call = 'put'
                    if day_residue_int > 2:
                        month_mall_type = 'center_index'
                        # center_index / center_index_45
                    else:
                        month_mall_type = 'center_index_45'
                        # center_index / center_index_45
                    item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                    # print(item_list_cnt)

                    # if d == 0:
                    #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                    # else:
                    #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                    # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                    for i in range(len(item_list_cnt['code_no'])):
                        if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:  # 첫번째 라인에서 저장한 코드와 동일할때
                            for j in range(len(item_list_cnt_items_search['code_no'])):  # 그 종목은 건수만 카운터 해주고
                                if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:  # 그 종목이랑 동일할때
                                    item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                        else:
                            item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                            item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                            item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                    # print(item_list_cnt_items_search)

                    # 텍스트 저장은 종목이 있을경우에만
                    if len(item_list_cnt['code_no']) > 0:
                        item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                        for s in range(len(item_list_cnt['code_no'])):
                            item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                            item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                        # 종목코드와 수량(텍스트에 저장하기)
                        self.today_put_order_list_text_store(item_list_cnt_for_store)

                    #  -----
                    # 검색결과 종목 vs option_myhave 비교하여 실제 거래항목 정하기
                    for s in range(len(item_list_cnt_items_search['code_no'])):
                        if item_list_cnt_items_search['code_no'][s] in self.option_myhave['code']:
                            for p in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][p] == item_list_cnt_items_search['code_no'][s]:
                                    # 재고가 혹시 매도
                                    if self.option_myhave['sell_or_buy'][p] == 1:
                                        if item_list_cnt_items_search['cnt'][s] > self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] - self.option_myhave['myhave_cnt'][p])
                                            item_list_cnt_type['sell_buy_type'].append(1)
                                        elif item_list_cnt_items_search['cnt'][s] < self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p] - item_list_cnt_items_search['cnt'][s])
                                            item_list_cnt_type['sell_buy_type'].append(2)
                                        elif item_list_cnt_items_search['cnt'][s] == self.option_myhave['myhave_cnt'][p]:
                                            pass
                                    # 재고가 행여나 매수
                                    elif self.option_myhave['sell_or_buy'][p] == 2:
                                        item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                        item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] + self.option_myhave['myhave_cnt'][p])
                                        item_list_cnt_type['sell_buy_type'].append(1)
                        else:
                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s])
                            item_list_cnt_type['sell_buy_type'].append(1)
                    # -----

                    # -----
                    # 만일 재고 항목이 검색항목에 없을때
                    for p in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][p] in item_list_cnt_items_search['code_no']:
                            pass
                        else:
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

                else:
                    # 당일 선물 진입여부 판단(없었을 경우) :: 텍스트 파일 삭제
                    # item_list.txt 저장경로
                    item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + 'today_put_order_lists.txt'
                    if os.path.exists(item_list_files_path):
                        os.remove(item_list_files_path)
                    # self.option_myhave = {'code': ['301SA307', '301SA310', '301SA315', '301SA317'],
                    #                       'myhave_cnt': [18, 15, 15, 3], 'sell_or_buy': [1, 1, 1, 1]}
                    # 301SA307::9::301SA310::15::301SA317::3::301SA315::5::
                    # 301SA307::9::301SA315::10::
                    # {'code_no': ['301SA307', '301SA315', '301SA310', '301SA317'], 'cnt': [18, 15, 15, 3], 'sell_buy_type': []}

                    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
                    future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
                    # self.printt('# future_s_simul_of_trend_line_day')
                    # self.printt(future_s_simul_of_trend_line_day)
                    for d in range(myhave_sell_total_mall_basket_cnt_remove - 2):
                        # 과거 시뮬레이션 값 가져와서 종목 찾기 & 주문할 종목코드 카운터 텍스트 저장
                        sell_mode_first = 0
                        sell_mode_cnt = 0
                        sell_ref_price = []
                        sell_second_price = []
                        # 시뮬레이터 구한 값 있을때만 실행
                        if future_s_simul_of_trend_line_day != None:
                            # sell_mode_cnt = 2
                            for i in range(len(future_s_simul_of_trend_line_day['deal_day'])):
                                # mode 더해보기(+-)
                                sell_mode_first += future_s_simul_of_trend_line_day['sell_mode'][i] - future_s_simul_of_trend_line_day['buy_mode'][i]
                                if sell_mode_first == (myhave_sell_total_mall_basket_cnt_remove - 2) - d:               # 역으로 today재고 저장
                                    sell_ref_price.append(future_s_simul_of_trend_line_day['poly_sell_max_price'][i])
                                    for j in range(i + 1, len(future_s_simul_of_trend_line_day['deal_day']) - 1):
                                        # mode 더해보기(+-)
                                        sell_mode_cnt += future_s_simul_of_trend_line_day['sell_mode'][
                                            j] - future_s_simul_of_trend_line_day['buy_mode'][j]
                                        if sell_mode_cnt == 2:
                                            sell_second_price.append(
                                                future_s_simul_of_trend_line_day['poly_sell_max_price'][j])
                                    break
                        # [315.06694648735436]
                        # print(sell_ref_price)
                        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
                        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
                        # print(sell_second_price)
                        # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(sell_ref_price[0] - sell_second_price[0])
                        option_s_point_sum += option_s_sell_buy_point
                        self.printt('sell_ref_price')
                        self.printt(sell_ref_price)
                        self.printt('sell_second_price')
                        self.printt(sell_second_price)
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)

                        # 옵션 종목검색()
                        put_or_call = 'put'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)

                        # if d == 0:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                        # else:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                        # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                        if d == 0:
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        else:
                            for i in range(len(item_list_cnt['code_no'])):
                                if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:                    # 첫번째 라인에서 저장한 코드와 동일할때
                                    for j in range(len(item_list_cnt_items_search['code_no'])):                             # 그 종목은 건수만 카운터 해주고
                                        if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:         # 그 종목이랑 동일할때
                                            item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                                else:
                                    item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                    item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        # print(item_list_cnt_items_search)

                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for s in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_put_order_list_text_store(item_list_cnt_for_store)

                    # 검색결과 종목 vs option_myhave 비교하여 실제 거래항목 정하기
                    for s in range(len(item_list_cnt_items_search['code_no'])):
                        if item_list_cnt_items_search['code_no'][s] in self.option_myhave['code']:
                            for p in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][p] == item_list_cnt_items_search['code_no'][s]:
                                    # 재고가 혹시 매도
                                    if self.option_myhave['sell_or_buy'][p] == 1:
                                        if item_list_cnt_items_search['cnt'][s] > self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] - self.option_myhave['myhave_cnt'][p])
                                            item_list_cnt_type['sell_buy_type'].append(1)
                                        elif item_list_cnt_items_search['cnt'][s] < self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p] - item_list_cnt_items_search['cnt'][s])
                                            item_list_cnt_type['sell_buy_type'].append(2)
                                        elif item_list_cnt_items_search['cnt'][s] == self.option_myhave['myhave_cnt'][p]:
                                            pass
                                    # 재고가 행여나 매수
                                    elif self.option_myhave['sell_or_buy'][p] == 2:
                                        item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                        item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] + self.option_myhave['myhave_cnt'][p])
                                        item_list_cnt_type['sell_buy_type'].append(1)
                        else:
                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s])
                            item_list_cnt_type['sell_buy_type'].append(1)
                    # 만일 재고 항목이 검색항목에 없을때
                    for p in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][p] in item_list_cnt_items_search['code_no']:
                            pass
                        else:
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
            else:
                # 만일 재고가 2이하 인데 옵션 재고가 있을 때
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

        # 선물 매수재고 => 콜청산(매수) 후 콜매도
        elif myhave_buy_total_mall_basket_cnt_remove > 0:
            self.printt('선물 매수재고 있음')
            if myhave_buy_total_mall_basket_cnt_remove >= 4:
                # 당일 선물 진입여부 판단
                # 당일 거래 있었으면 텍스트 파일 호출 / 없었으면 시뮬레이터 계산
                if (self.futrue_s_data['item_code'][0] in self.buyed_today_items) or (
                        self.futrue_s_data_45['item_code'][0] in self.buyed_today_items) or (
                        Chain_Future_s_Item_Code[0] in self.buyed_today_items):
                    # item_list.txt 저장경로
                    item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + 'today_call_order_lists.txt'
                    if os.path.exists(item_list_files_path):
                        os.remove(item_list_files_path)
                    # self.option_myhave = {'code': ['201SA307', '201SA310', '201SA315', '201SA317'],
                    #                       'myhave_cnt': [18, 15, 15, 3], 'sell_or_buy': [1, 1, 1, 1]}
                    # 201SA307::9::201SA310::15::201SA317::3::201SA315::5::
                    # 201SA307::9::201SA315::10::
                    # {'code_no': ['201SA307', '201SA315', '201SA310', '201SA317'], 'cnt': [18, 15, 15, 3], 'sell_buy_type': []}

                    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
                    future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
                    # self.printt('# future_s_simul_of_trend_line_day')
                    # self.printt(future_s_simul_of_trend_line_day)
                    for d in range(myhave_buy_total_mall_basket_cnt_remove - 2 - 1):
                        # 과거 시뮬레이션 값 가져와서 종목 찾기 & 주문할 종목코드 카운터 텍스트 저장
                        buy_mode_first = 0
                        buy_mode_cnt = 0
                        buy_ref_price = []
                        buy_second_price = []
                        # 시뮬레이터 구한 값 있을때만 실행
                        if future_s_simul_of_trend_line_day != None:
                            # sell_mode_cnt = 2
                            for i in range(len(future_s_simul_of_trend_line_day['deal_day'])):
                                # mode 더해보기(+-)
                                buy_mode_first += future_s_simul_of_trend_line_day['buy_mode'][i] - future_s_simul_of_trend_line_day['sell_mode'][i]
                                if buy_mode_first == (myhave_buy_total_mall_basket_cnt_remove - 2) - d:               # 역으로 today재고 저장
                                    buy_ref_price.append(future_s_simul_of_trend_line_day['poly_buy_min_price'][i])
                                    for j in range(i + 1, len(future_s_simul_of_trend_line_day['deal_day']) - 1):
                                        # mode 더해보기(+-)
                                        buy_mode_cnt += future_s_simul_of_trend_line_day['buy_mode'][j] - future_s_simul_of_trend_line_day['sell_mode'][j]
                                        if buy_mode_cnt == 2:
                                            buy_second_price.append(
                                                future_s_simul_of_trend_line_day['poly_buy_min_price'][j])
                                    break
                        # [315.06694648735436]
                        # print(buy_ref_price)
                        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
                        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
                        # print(buy_second_price)
                        # 지난진입 금액확인 :: 옵션매도 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(buy_ref_price[0] - buy_second_price[0])
                        option_s_point_sum += option_s_sell_buy_point
                        self.printt('buy_ref_price')
                        self.printt(buy_ref_price)
                        self.printt('buy_second_price')
                        self.printt(buy_second_price)
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)

                        # 옵션 종목검색()
                        put_or_call = 'call'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)

                        # if d == 0:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                        # else:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                        # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                        if d == 0:
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        else:
                            for i in range(len(item_list_cnt['code_no'])):
                                if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:                    # 첫번째 라인에서 저장한 코드와 동일할때
                                    for j in range(len(item_list_cnt_items_search['code_no'])):                             # 그 종목은 건수만 카운터 해주고
                                        if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:         # 그 종목이랑 동일할때
                                            item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                                else:
                                    item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                    item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        # print(item_list_cnt_items_search)

                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for s in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_call_order_list_text_store(item_list_cnt_for_store)

                    # option_s_sell_buy_point_text 가져오기
                    option_s_sell_buy_point_text_list = self.option_s_sell_buy_point_text_pickup()
                    # print(option_s_sell_buy_point_text_list)
                    option_s_sell_buy_point = option_s_sell_buy_point_text_list[-1]
                    # print(option_s_sell_buy_point)
                    option_s_point_sum += option_s_sell_buy_point
                    self.printt('option_s_sell_buy_point')
                    self.printt(option_s_sell_buy_point)

                    # 옵션 종목검색()
                    put_or_call = 'call'
                    if day_residue_int > 2:
                        month_mall_type = 'center_index'
                        # center_index / center_index_45
                    else:
                        month_mall_type = 'center_index_45'
                        # center_index / center_index_45
                    item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                    # print(item_list_cnt)

                    # if d == 0:
                    #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                    # else:
                    #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                    # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                    for i in range(len(item_list_cnt['code_no'])):
                        if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:  # 첫번째 라인에서 저장한 코드와 동일할때
                            for j in range(len(item_list_cnt_items_search['code_no'])):  # 그 종목은 건수만 카운터 해주고
                                if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:  # 그 종목이랑 동일할때
                                    item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                        else:
                            item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                            item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                            item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                    # print(item_list_cnt_items_search)

                    # 텍스트 저장은 종목이 있을경우에만
                    if len(item_list_cnt['code_no']) > 0:
                        item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                        for s in range(len(item_list_cnt['code_no'])):
                            item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                            item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                        # 종목코드와 수량(텍스트에 저장하기)
                        self.today_call_order_list_text_store(item_list_cnt_for_store)

                    # 검색결과 종목 vs option_myhave 비교하여 실제 거래항목 정하기
                    for s in range(len(item_list_cnt_items_search['code_no'])):
                        if item_list_cnt_items_search['code_no'][s] in self.option_myhave['code']:
                            for p in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][p] == item_list_cnt_items_search['code_no'][s]:
                                    # 재고가 혹시 매도
                                    if self.option_myhave['sell_or_buy'][p] == 1:
                                        if item_list_cnt_items_search['cnt'][s] > self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] - self.option_myhave['myhave_cnt'][p])
                                            item_list_cnt_type['sell_buy_type'].append(1)
                                        elif item_list_cnt_items_search['cnt'][s] < self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p] - item_list_cnt_items_search['cnt'][s])
                                            item_list_cnt_type['sell_buy_type'].append(2)
                                        elif item_list_cnt_items_search['cnt'][s] == self.option_myhave['myhave_cnt'][p]:
                                            pass
                                    # 재고가 행여나 매수
                                    elif self.option_myhave['sell_or_buy'][p] == 2:
                                        item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                        item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] + self.option_myhave['myhave_cnt'][p])
                                        item_list_cnt_type['sell_buy_type'].append(1)

                        else:
                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s])
                            item_list_cnt_type['sell_buy_type'].append(1)

                    # 만일 재고 항목이 검색항목에 없을때
                    for p in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][p] in item_list_cnt_items_search['code_no']:
                            pass
                        else:
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
                else:
                    # 당일 선물 진입여부 판단(없었을 경우)
                    # item_list.txt 저장경로
                    item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + 'today_call_order_lists.txt'
                    if os.path.exists(item_list_files_path):
                        os.remove(item_list_files_path)
                    # self.option_myhave = {'code': ['201SA307', '201SA310', '201SA315', '201SA317'],
                    #                       'myhave_cnt': [18, 15, 15, 3], 'sell_or_buy': [1, 1, 1, 1]}
                    # 201SA307::9::201SA310::15::201SA317::3::201SA315::5::
                    # 201SA307::9::201SA315::10::
                    # {'code_no': ['201SA307', '201SA315', '201SA310', '201SA317'], 'cnt': [18, 15, 15, 3], 'sell_buy_type': []}

                    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
                    future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
                    # self.printt('# future_s_simul_of_trend_line_day')
                    # self.printt(future_s_simul_of_trend_line_day)
                    for d in range(myhave_buy_total_mall_basket_cnt_remove - 2):
                        # 과거 시뮬레이션 값 가져와서 종목 찾기 & 주문할 종목코드 카운터 텍스트 저장
                        buy_mode_first = 0
                        buy_mode_cnt = 0
                        buy_ref_price = []
                        buy_second_price = []
                        # 시뮬레이터 구한 값 있을때만 실행
                        if future_s_simul_of_trend_line_day != None:
                            # sell_mode_cnt = 2
                            for i in range(len(future_s_simul_of_trend_line_day['deal_day'])):
                                # mode 더해보기(+-)
                                buy_mode_first += future_s_simul_of_trend_line_day['buy_mode'][i] - future_s_simul_of_trend_line_day['sell_mode'][i]
                                if buy_mode_first == (myhave_buy_total_mall_basket_cnt_remove - 2) - d:               # 역으로 today재고 저장
                                    buy_ref_price.append(future_s_simul_of_trend_line_day['poly_buy_min_price'][i])
                                    for j in range(i + 1, len(future_s_simul_of_trend_line_day['deal_day']) - 1):
                                        # mode 더해보기(+-)
                                        buy_mode_cnt += future_s_simul_of_trend_line_day['buy_mode'][j] - future_s_simul_of_trend_line_day['sell_mode'][j]
                                        if buy_mode_cnt == 2:
                                            buy_second_price.append(
                                                future_s_simul_of_trend_line_day['poly_buy_min_price'][j])
                                    break
                        # [315.06694648735436]
                        # print(buy_ref_price)
                        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
                        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
                        # print(buy_second_price)
                        # 지난진입 금액확인 :: 옵션매도 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(buy_ref_price[0] - buy_second_price[0])
                        option_s_point_sum += option_s_sell_buy_point
                        self.printt('buy_ref_price')
                        self.printt(buy_ref_price)
                        self.printt('buy_second_price')
                        self.printt(buy_second_price)
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)

                        # 옵션 종목검색()
                        put_or_call = 'call'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)

                        # if d == 0:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                        # else:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                        # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                        if d == 0:
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        else:
                            for i in range(len(item_list_cnt['code_no'])):
                                if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:                    # 첫번째 라인에서 저장한 코드와 동일할때
                                    for j in range(len(item_list_cnt_items_search['code_no'])):                             # 그 종목은 건수만 카운터 해주고
                                        if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:         # 그 종목이랑 동일할때
                                            item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                                else:
                                    item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                    item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        # print(item_list_cnt_items_search)

                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for s in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_call_order_list_text_store(item_list_cnt_for_store)

                    # 검색결과 종목 vs option_myhave 비교하여 실제 거래항목 정하기
                    for s in range(len(item_list_cnt_items_search['code_no'])):
                        if item_list_cnt_items_search['code_no'][s] in self.option_myhave['code']:
                            for p in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][p] == item_list_cnt_items_search['code_no'][s]:
                                    # 재고가 혹시 매도
                                    if self.option_myhave['sell_or_buy'][p] == 1:
                                        if item_list_cnt_items_search['cnt'][s] > self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] - self.option_myhave['myhave_cnt'][p])
                                            item_list_cnt_type['sell_buy_type'].append(1)
                                        elif item_list_cnt_items_search['cnt'][s] < self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p] - item_list_cnt_items_search['cnt'][s])
                                            item_list_cnt_type['sell_buy_type'].append(2)
                                        elif item_list_cnt_items_search['cnt'][s] == self.option_myhave['myhave_cnt'][p]:
                                            pass
                                    # 재고가 행여나 매수
                                    elif self.option_myhave['sell_or_buy'][p] == 2:
                                        item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                        item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] + self.option_myhave['myhave_cnt'][p])
                                        item_list_cnt_type['sell_buy_type'].append(1)

                        else:
                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s])
                            item_list_cnt_type['sell_buy_type'].append(1)

                    # 만일 재고 항목이 검색항목에 없을때
                    for p in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][p] in item_list_cnt_items_search['code_no']:
                            pass
                        else:
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
            # 선물 매수재고(3)
            elif myhave_buy_total_mall_basket_cnt_remove == 3:
                # 당일 선물 진입여부 판단
                # 당일 거래 있었으면 텍스트 파일 호출 / 없었으면 시뮬레이터 계산
                if (self.futrue_s_data['item_code'][0] in self.buyed_today_items) or (
                        self.futrue_s_data_45['item_code'][0] in self.buyed_today_items) or (
                        Chain_Future_s_Item_Code[0] in self.buyed_today_items):
                    # item_list.txt 저장경로
                    item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + 'today_call_order_lists.txt'
                    if os.path.exists(item_list_files_path):
                        os.remove(item_list_files_path)
                    # self.option_myhave = {'code': ['201SA307', '201SA310', '201SA315', '201SA317'],
                    #                       'myhave_cnt': [18, 15, 15, 3], 'sell_or_buy': [1, 1, 1, 1]}
                    # 201SA307::9::201SA310::15::201SA317::3::201SA315::5::
                    # 201SA307::9::201SA315::10::
                    # {'code_no': ['201SA307', '201SA315', '201SA310', '201SA317'], 'cnt': [18, 15, 15, 3], 'sell_buy_type': []}

                    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
                    future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
                    # self.printt('# future_s_simul_of_trend_line_day')
                    # self.printt(future_s_simul_of_trend_line_day)
                    for d in range(myhave_buy_total_mall_basket_cnt_remove - 2 - 1):
                        # 과거 시뮬레이션 값 가져와서 종목 찾기 & 주문할 종목코드 카운터 텍스트 저장
                        buy_mode_first = 0
                        buy_mode_cnt = 0
                        buy_ref_price = []
                        buy_second_price = []
                        # 시뮬레이터 구한 값 있을때만 실행
                        if future_s_simul_of_trend_line_day != None:
                            # sell_mode_cnt = 2
                            for i in range(len(future_s_simul_of_trend_line_day['deal_day'])):
                                # mode 더해보기(+-)
                                buy_mode_first += future_s_simul_of_trend_line_day['buy_mode'][i] - future_s_simul_of_trend_line_day['sell_mode'][i]
                                if buy_mode_first == (myhave_buy_total_mall_basket_cnt_remove - 2) - d:               # 역으로 today재고 저장
                                    buy_ref_price.append(future_s_simul_of_trend_line_day['poly_buy_min_price'][i])
                                    for j in range(i + 1, len(future_s_simul_of_trend_line_day['deal_day']) - 1):
                                        # mode 더해보기(+-)
                                        buy_mode_cnt += future_s_simul_of_trend_line_day['buy_mode'][j] - future_s_simul_of_trend_line_day['sell_mode'][j]
                                        if buy_mode_cnt == 2:
                                            buy_second_price.append(
                                                future_s_simul_of_trend_line_day['poly_buy_min_price'][j])
                                    break
                        # [315.06694648735436]
                        # print(buy_ref_price)
                        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
                        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
                        # print(buy_second_price)
                        # 지난진입 금액확인 :: 옵션매도 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(buy_ref_price[0] - buy_second_price[0])
                        option_s_point_sum += option_s_sell_buy_point
                        self.printt('buy_ref_price')
                        self.printt(buy_ref_price)
                        self.printt('buy_second_price')
                        self.printt(buy_second_price)
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)

                        # 옵션 종목검색()
                        put_or_call = 'call'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)

                        # if d == 0:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                        # else:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                        # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                        if d == 0:
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        else:
                            for i in range(len(item_list_cnt['code_no'])):
                                if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:                    # 첫번째 라인에서 저장한 코드와 동일할때
                                    for j in range(len(item_list_cnt_items_search['code_no'])):                             # 그 종목은 건수만 카운터 해주고
                                        if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:         # 그 종목이랑 동일할때
                                            item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                                else:
                                    item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                    item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        # print(item_list_cnt_items_search)

                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for s in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_call_order_list_text_store(item_list_cnt_for_store)

                    # option_s_sell_buy_point_text 가져오기
                    option_s_sell_buy_point_text_list = self.option_s_sell_buy_point_text_pickup()
                    # print(option_s_sell_buy_point_text_list)
                    option_s_sell_buy_point = option_s_sell_buy_point_text_list[-1]
                    # print(option_s_sell_buy_point)
                    option_s_point_sum += option_s_sell_buy_point
                    self.printt('option_s_sell_buy_point')
                    self.printt(option_s_sell_buy_point)

                    # 옵션 종목검색()
                    put_or_call = 'call'
                    if day_residue_int > 2:
                        month_mall_type = 'center_index'
                        # center_index / center_index_45
                    else:
                        month_mall_type = 'center_index_45'
                        # center_index / center_index_45
                    item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                    # print(item_list_cnt)

                    # if d == 0:
                    #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                    # else:
                    #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                    # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                    for i in range(len(item_list_cnt['code_no'])):
                        if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:  # 첫번째 라인에서 저장한 코드와 동일할때
                            for j in range(len(item_list_cnt_items_search['code_no'])):  # 그 종목은 건수만 카운터 해주고
                                if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:  # 그 종목이랑 동일할때
                                    item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                        else:
                            item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                            item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                            item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                    # print(item_list_cnt_items_search)

                    # 텍스트 저장은 종목이 있을경우에만
                    if len(item_list_cnt['code_no']) > 0:
                        item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                        for s in range(len(item_list_cnt['code_no'])):
                            item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                            item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                        # 종목코드와 수량(텍스트에 저장하기)
                        self.today_call_order_list_text_store(item_list_cnt_for_store)

                    # 검색결과 종목 vs option_myhave 비교하여 실제 거래항목 정하기
                    for s in range(len(item_list_cnt_items_search['code_no'])):
                        if item_list_cnt_items_search['code_no'][s] in self.option_myhave['code']:
                            for p in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][p] == item_list_cnt_items_search['code_no'][s]:
                                    # 재고가 혹시 매도
                                    if self.option_myhave['sell_or_buy'][p] == 1:
                                        if item_list_cnt_items_search['cnt'][s] > self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] - self.option_myhave['myhave_cnt'][p])
                                            item_list_cnt_type['sell_buy_type'].append(1)
                                        elif item_list_cnt_items_search['cnt'][s] < self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p] - item_list_cnt_items_search['cnt'][s])
                                            item_list_cnt_type['sell_buy_type'].append(2)
                                        elif item_list_cnt_items_search['cnt'][s] == self.option_myhave['myhave_cnt'][p]:
                                            pass
                                    # 재고가 행여나 매수
                                    elif self.option_myhave['sell_or_buy'][p] == 2:
                                        item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                        item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] + self.option_myhave['myhave_cnt'][p])
                                        item_list_cnt_type['sell_buy_type'].append(1)

                        else:
                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s])
                            item_list_cnt_type['sell_buy_type'].append(1)

                    # 만일 재고 항목이 검색항목에 없을때
                    for p in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][p] in item_list_cnt_items_search['code_no']:
                            pass
                        else:
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
                else:
                    # 당일 선물 진입여부 판단(없었을 경우)
                    # item_list.txt 저장경로
                    item_list_files_path = os.getcwd() + '/' + Folder_Name_TXT_Store + '/' + 'today_call_order_lists.txt'
                    if os.path.exists(item_list_files_path):
                        os.remove(item_list_files_path)
                    # self.option_myhave = {'code': ['201SA307', '201SA310', '201SA315', '201SA317'],
                    #                       'myhave_cnt': [18, 15, 15, 3], 'sell_or_buy': [1, 1, 1, 1]}
                    # 201SA307::9::201SA310::15::201SA317::3::201SA315::5::
                    # 201SA307::9::201SA315::10::
                    # {'code_no': ['201SA307', '201SA315', '201SA310', '201SA317'], 'cnt': [18, 15, 15, 3], 'sell_buy_type': []}

                    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
                    future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
                    # self.printt('# future_s_simul_of_trend_line_day')
                    # self.printt(future_s_simul_of_trend_line_day)
                    for d in range(myhave_buy_total_mall_basket_cnt_remove - 2):
                        # 과거 시뮬레이션 값 가져와서 종목 찾기 & 주문할 종목코드 카운터 텍스트 저장
                        buy_mode_first = 0
                        buy_mode_cnt = 0
                        buy_ref_price = []
                        buy_second_price = []
                        # 시뮬레이터 구한 값 있을때만 실행
                        if future_s_simul_of_trend_line_day != None:
                            # sell_mode_cnt = 2
                            for i in range(len(future_s_simul_of_trend_line_day['deal_day'])):
                                # mode 더해보기(+-)
                                buy_mode_first += future_s_simul_of_trend_line_day['buy_mode'][i] - future_s_simul_of_trend_line_day['sell_mode'][i]
                                if buy_mode_first == (myhave_buy_total_mall_basket_cnt_remove - 2) - d:               # 역으로 today재고 저장
                                    buy_ref_price.append(future_s_simul_of_trend_line_day['poly_buy_min_price'][i])
                                    for j in range(i + 1, len(future_s_simul_of_trend_line_day['deal_day']) - 1):
                                        # mode 더해보기(+-)
                                        buy_mode_cnt += future_s_simul_of_trend_line_day['buy_mode'][j] - future_s_simul_of_trend_line_day['sell_mode'][j]
                                        if buy_mode_cnt == 2:
                                            buy_second_price.append(
                                                future_s_simul_of_trend_line_day['poly_buy_min_price'][j])
                                    break
                        # [315.06694648735436]
                        # print(buy_ref_price)
                        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
                        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
                        # print(buy_second_price)
                        # 지난진입 금액확인 :: 옵션매도 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(buy_ref_price[0] - buy_second_price[0])
                        option_s_point_sum += option_s_sell_buy_point
                        self.printt('buy_ref_price')
                        self.printt(buy_ref_price)
                        self.printt('buy_second_price')
                        self.printt(buy_second_price)
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)

                        # 옵션 종목검색()
                        put_or_call = 'call'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)

                        # if d == 0:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA310'], 'cnt': [3, 5]}   # option_items_search 결과값
                        # else:
                        #     item_list_cnt = {'code_no': ['201SA307', '201SA315', '201SA317'], 'cnt': [3, 5, 1]}

                        # 종목코드 중복시 건수만 늘려주고(중복된것 모두 정리하기)
                        if d == 0:
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        else:
                            for i in range(len(item_list_cnt['code_no'])):
                                if item_list_cnt['code_no'][i] in item_list_cnt_items_search['code_no']:                    # 첫번째 라인에서 저장한 코드와 동일할때
                                    for j in range(len(item_list_cnt_items_search['code_no'])):                             # 그 종목은 건수만 카운터 해주고
                                        if item_list_cnt_items_search['code_no'][j] == item_list_cnt['code_no'][i]:         # 그 종목이랑 동일할때
                                            item_list_cnt_items_search['cnt'][j] += (item_list_cnt['cnt'][i] * basket_cnt)
                                else:
                                    item_list_cnt_items_search['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_items_search['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                    item_list_cnt_items_search['point'].append(item_list_cnt['point'][i])
                        # print(item_list_cnt_items_search)

                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for s in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][s])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][s] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_call_order_list_text_store(item_list_cnt_for_store)

                    # 검색결과 종목 vs option_myhave 비교하여 실제 거래항목 정하기
                    for s in range(len(item_list_cnt_items_search['code_no'])):
                        if item_list_cnt_items_search['code_no'][s] in self.option_myhave['code']:
                            for p in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][p] == item_list_cnt_items_search['code_no'][s]:
                                    # 재고가 혹시 매도
                                    if self.option_myhave['sell_or_buy'][p] == 1:
                                        if item_list_cnt_items_search['cnt'][s] > self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] - self.option_myhave['myhave_cnt'][p])
                                            item_list_cnt_type['sell_buy_type'].append(1)
                                        elif item_list_cnt_items_search['cnt'][s] < self.option_myhave['myhave_cnt'][p]:
                                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                            item_list_cnt_type['cnt'].append(self.option_myhave['myhave_cnt'][p] - item_list_cnt_items_search['cnt'][s])
                                            item_list_cnt_type['sell_buy_type'].append(2)
                                        elif item_list_cnt_items_search['cnt'][s] == self.option_myhave['myhave_cnt'][p]:
                                            pass
                                    # 재고가 행여나 매수
                                    elif self.option_myhave['sell_or_buy'][p] == 2:
                                        item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                                        item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s] + self.option_myhave['myhave_cnt'][p])
                                        item_list_cnt_type['sell_buy_type'].append(1)

                        else:
                            item_list_cnt_type['code_no'].append(item_list_cnt_items_search['code_no'][s])
                            item_list_cnt_type['cnt'].append(item_list_cnt_items_search['cnt'][s])
                            item_list_cnt_type['sell_buy_type'].append(1)

                    # 만일 재고 항목이 검색항목에 없을때
                    for p in range(len(self.option_myhave['code'])):
                        if self.option_myhave['code'][p] in item_list_cnt_items_search['code_no']:
                            pass
                        else:
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
            else:
                # 만일 재고가 2이하 인데 옵션 재고가 있을 때
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
        # 현재의 선물 매도/매수 옵션 매도/매수 상황에 따른 자산가치 정리해서 db저장
        # db명
        db_name_center_option_s_change_data = 'center_option_s_change_state'
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
        center_option_s_change_data['option_s_point_sum'].append(option_s_point_sum)
        # 현재 옵션 투입(검색결과) point 합계
        option_s_point_in = 0
        for i in range(len(item_list_cnt_items_search['code_no'])):
            option_s_point_in += item_list_cnt_items_search['cnt'][i] * item_list_cnt_items_search['point'][i]
        center_option_s_change_data['option_s_point_in'].append(option_s_point_in)
        # 현재 옵션 재고 point 합계
        option_s_point_myhave = 0
        # 풋옵션
        for i in range(len(self.output_put_option_data['code'])):
            for h in range(len(self.option_myhave['code'])):
                # 재고가 매도
                if self.option_myhave['sell_or_buy'][h] == 1:
                    if self.output_put_option_data['code'][i] == self.option_myhave['code'][h]:
                        option_s_point_myhave += self.output_put_option_data['run_price'][i] * self.option_myhave['myhave_cnt'][h]
        # 차월물
        for i in range(len(self.output_put_option_data_45['code'])):
            for h in range(len(self.option_myhave['code'])):
                # 재고가 매도
                if self.option_myhave['sell_or_buy'][h] == 1:
                    if self.output_put_option_data_45['code'][i] == self.option_myhave['code'][h]:
                        option_s_point_myhave += self.output_put_option_data_45['run_price'][i] * self.option_myhave['myhave_cnt'][h]
        # 콜옵션
        for i in range(len(self.output_call_option_data['code'])):
            for h in range(len(self.option_myhave['code'])):
                # 재고가 매도
                if self.option_myhave['sell_or_buy'][h] == 1:
                    if self.output_call_option_data['code'][i] == self.option_myhave['code'][h]:
                        option_s_point_myhave += self.output_call_option_data['run_price'][i] * self.option_myhave['myhave_cnt'][h]
        # 차월물
        for i in range(len(self.output_call_option_data_45['code'])):
            for h in range(len(self.option_myhave['code'])):
                # 재고가 매도
                if self.option_myhave['sell_or_buy'][h] == 1:
                    if self.output_call_option_data_45['code'][i] == self.option_myhave['code'][h]:
                        option_s_point_myhave += self.output_call_option_data_45['run_price'][i] * self.option_myhave['myhave_cnt'][h]
        center_option_s_change_data['option_s_point_myhave'].append(option_s_point_myhave)
        center_option_s_change_data['day_residue_int'].append(day_residue_int)
        # 선물옵션 순자산금액 + stock 추정예탁자산
        option_have_money_plus_estimated_deposit = self.option_have_money + self.estimated_deposit
        center_option_s_change_data['my_total_money'].append(option_have_money_plus_estimated_deposit)
        # 저장 함수 호출
        center_option_s_change_data_store(Folder_Name_DB_Store, db_name_center_option_s_change_data, center_option_s_change_data)
        # -----

        # -----
        self.printt('중심가 변경시 옵션 튜닝 결색결과 리스트')
        self.printt(item_list_cnt_type)

        for r in range(len(item_list_cnt_type['code_no'])):
            if item_list_cnt_type['sell_buy_type'][r] == 1:
                # 이번 중심가 변경시 옵션매도 주문 가능 건수
                print(self.option_order_able_money)
                print(self.option_s_sell_order_deposit_money)
                now_option_s_sell_order_able_cnt = math.floor(self.option_order_able_money / self.option_s_sell_order_deposit_money)
                if item_list_cnt_type['cnt'][r] > now_option_s_sell_order_able_cnt:
                    item_list_cnt_type['cnt'][r] = now_option_s_sell_order_able_cnt

        self.printt('옵션 매도 최대금액 감안 리스트')
        self.printt(item_list_cnt_type)
        # -----

        # 검색된 종목코드 여부
        item_list_cnt = len(item_list_cnt_type['code_no'])
        if item_list_cnt > 0:
            self.future_s_market_sell_buy(item_list_cnt_type)

    # 선물(진입/청산) 옵션(진입/청산) 준비
    def future_s_market_ready(self):
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

        # 주문변수 초기화
        item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 선물 바스켓 가져오기
        basket_cnt = self.future_s_basket_cnt_text_read()   #int
        # print(basket_cnt)

        # 계좌잔고 시세요청
        self.stock_have_data_rq()
        # # 테이블 위젯에 표시하기
        # self.stock_listed_slot(self.stock_have_data)
        # 서버에서 수신받은 stock_data
        self.printt('# 서버에서 수신받은 stock_data')
        self.printt(len(self.stock_have_data['stock_no']))
        self.printt(self.stock_have_data)

        # 선옵잔고요청 - 이벤트 슬롯
        self.myhave_option_rq()
        # # 예탁금및증거금조회 - 이벤트 슬롯
        # self.mymoney_option_rq()
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
        if self.stock_trend_line_of_ai_day != None:
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
                # 롤오버 감안 미리 차월물 진입 여부
                # 재고수량과 비교하여 잔존일이 2일 이상 남았으면 당월물 그렇지 않으면 차월물
                if myhave_sell_current_mall_cnt > 0:
                    self.printt('매도재고 있음')
                    sell_roll_over_check_cnt = int(myhave_sell_current_mall_cnt / basket_cnt)
                    if future_s_day_residue_int > (sell_roll_over_check_cnt + 2):
                        self.printt('당월물 진입')

                        # 선물재고 건수 및 옵션재고 확인
                        if myhave_sell_total_mall_basket_cnt_remove >= 4:
                            # 매도재고 : 매도신호 => 선물매도 건수가 바스켓 기준으로 4이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                            self.printt('(4)선물매도 건수가 바스켓 기준으로 4이상이면 거래없음')
                            # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                            option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                          self.sell_second_price[0])
                            self.printt('self.futrue_s_data[run_price][0]')
                            self.printt(self.futrue_s_data['run_price'][0])
                            self.printt('self.sell_second_price[0]')
                            self.printt(self.sell_second_price[0])
                            self.printt('option_s_sell_buy_point')
                            self.printt(option_s_sell_buy_point)
                            # option_s_sell_buy_point 텍스트 저장
                            self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                            # 연결선물가상매매
                            SellBuyType = '매도'
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            time_msg = ' 연결선물가상매매 : ' + text_time
                            # 텍스트 저장 호출
                            self.printt_selled(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                            return
                        elif (myhave_sell_total_mall_basket_cnt_remove == 3) or (
                                myhave_sell_total_mall_basket_cnt_remove == 2):
                            # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                            option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                          self.sell_second_price[0])
                            self.printt('self.futrue_s_data[run_price][0]')
                            self.printt(self.futrue_s_data['run_price'][0])
                            self.printt('self.sell_second_price[0]')
                            self.printt(self.sell_second_price[0])
                            self.printt('option_s_sell_buy_point')
                            self.printt(option_s_sell_buy_point)
                            # option_s_sell_buy_point 텍스트 저장
                            self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                            # 옵션 종목검색(풋매도)
                            put_or_call = 'put'
                            if day_residue_int > 2:
                                month_mall_type = 'center_index'
                                # center_index / center_index_45
                            else:
                                month_mall_type = 'center_index_45'
                                # center_index / center_index_45
                            item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                            # print(item_list_cnt)
                            # item_list_cnt = {'code_no': ['301SA307'], 'cnt': [3]}   # 텍스트 읽은 결과값
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_type['sell_buy_type'].append(1)
                            self.printt('(3~2)옵션 종목검색(풋매도)')
                            self.printt(item_list_cnt_type)
                            # 텍스트 저장은 종목이 있을경우에만
                            if len(item_list_cnt['code_no']) > 0:
                                item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                                for i in range(len(item_list_cnt['code_no'])):
                                    item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                # 종목코드와 수량(텍스트에 저장하기)
                                self.today_put_order_list_text_store(item_list_cnt_for_store)
                        elif myhave_sell_total_mall_basket_cnt_remove == 1:
                            # 일반 진입
                            self.printt('(1)일반 진입')
                            pass

                        # 선물매도
                        item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                        item_list_cnt_type['cnt'].append(basket_cnt)
                        item_list_cnt_type['sell_buy_type'].append(1)
                        # print(item_list_cnt_type)

                    elif future_s_day_residue_int <= (sell_roll_over_check_cnt + 2):
                        self.printt('차월물 진입')

                        # 선물재고 건수 및 옵션재고 확인
                        if myhave_sell_total_mall_basket_cnt_remove >= 4:
                            # 매도재고 : 매도신호 => 선물매도 건수가 바스켓 기준으로 4이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                            self.printt('(4)선물매도 건수가 바스켓 기준으로 4이상이면 거래없음')
                            # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                            option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                          self.sell_second_price[0])
                            self.printt('self.futrue_s_data[run_price][0]')
                            self.printt(self.futrue_s_data['run_price'][0])
                            self.printt('self.sell_second_price[0]')
                            self.printt(self.sell_second_price[0])
                            self.printt('option_s_sell_buy_point')
                            self.printt(option_s_sell_buy_point)
                            # option_s_sell_buy_point 텍스트 저장
                            self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                            # 연결선물가상매매
                            SellBuyType = '매도'
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            time_msg = ' 연결선물가상매매 : ' + text_time
                            # 텍스트 저장 호출
                            self.printt_selled(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                            return
                        elif (myhave_sell_total_mall_basket_cnt_remove == 3) or (
                                myhave_sell_total_mall_basket_cnt_remove == 2):
                            # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                            option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                          self.sell_second_price[0])
                            self.printt('self.futrue_s_data[run_price][0]')
                            self.printt(self.futrue_s_data['run_price'][0])
                            self.printt('self.sell_second_price[0]')
                            self.printt(self.sell_second_price[0])
                            self.printt('option_s_sell_buy_point')
                            self.printt(option_s_sell_buy_point)
                            # option_s_sell_buy_point 텍스트 저장
                            self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                            # 옵션 종목검색(풋매도)
                            put_or_call = 'put'
                            if day_residue_int > 2:
                                month_mall_type = 'center_index'
                                # center_index / center_index_45
                            else:
                                month_mall_type = 'center_index_45'
                                # center_index / center_index_45
                            item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                            # print(item_list_cnt)
                            # item_list_cnt = {'code_no': ['301SA307'], 'cnt': [3]}   # 텍스트 읽은 결과값
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_type['sell_buy_type'].append(1)
                            self.printt('(3~2)옵션 종목검색(풋매도)')
                            self.printt(item_list_cnt_type)
                            # 텍스트 저장은 종목이 있을경우에만
                            if len(item_list_cnt['code_no']) > 0:
                                item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                                for i in range(len(item_list_cnt['code_no'])):
                                    item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                # 종목코드와 수량(텍스트에 저장하기)
                                self.today_put_order_list_text_store(item_list_cnt_for_store)
                        elif myhave_sell_total_mall_basket_cnt_remove == 1:
                            # 일반 진입
                            self.printt('(1)일반 진입')
                            pass

                        # 선물매도
                        item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                        item_list_cnt_type['cnt'].append(basket_cnt)
                        item_list_cnt_type['sell_buy_type'].append(1)
                        # print(item_list_cnt_type)

                elif myhave_buy_current_mall_cnt > 0:
                    self.printt('매수재고 있음')
                    self.printt('당월물 청산')

                    # 조건확인
                    # 콜재고 있을때
                    call_my_have_str = ''
                    for p in range(len(self.option_myhave['code'])):
                        # print(self.option_myhave['code'][p][:3])
                        if self.option_myhave['code'][p][:3] == '201':
                            call_my_have_str = '201'
                            # 매도
                            if self.option_myhave['sell_or_buy'][p] == 1:
                                # print('콜매도 재고있음')
                                call_my_have_str = '2011'
                    if call_my_have_str == '2011':
                        # 매수재고 : 매도신호 => 선물매도(콜매수 청산)
                        # 종목코드와 수량 (텍스트에서 읽어오기)
                        item_list_cnt = self.today_call_order_list_text_pickup()
                        # {'code_no': ['201S2410', '201S2400', '201S2380'], 'cnt': [1, 2, 2]}
                        # 청산은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            # 선물매도/풋청산
                            for have in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][have][:3] == '201':
                                    if self.option_myhave['sell_or_buy'][have] == 1:
                                        for i in range(len(item_list_cnt['code_no'])):
                                            if self.option_myhave['code'][have] == item_list_cnt['code_no'][i]:
                                                if self.option_myhave['myhave_cnt'][have] >= item_list_cnt['cnt'][i]:
                                                    item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                                                    item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i])
                                                    item_list_cnt_type['sell_buy_type'].append(2)

                    # 선물매도
                    item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
                    # print(item_list_cnt_type)
            elif self.futrue_s_data['run_price'][0] < day_poly_min_price:
                self.printt('당월물 재고있음 선물매수(2) 신호발생')
                # 롤오버 감안 미리 차월물 진입 여부
                # 재고수량과 비교하여 잔존일이 2일 이상 남았으면 당월물 그렇지 않으면 차월물
                if myhave_sell_current_mall_cnt > 0:
                    self.printt('매도재고 있음')
                    self.printt('당월물 청산')

                    # 조건확인
                    # 풋재고 있을때
                    put_my_have_str = ''
                    for c in range(len(self.option_myhave['code'])):
                        # print(self.option_myhave['code'][c][:3])
                        if self.option_myhave['code'][c][:3] == '301':
                            put_my_have_str = '301'
                            # 매도
                            if self.option_myhave['sell_or_buy'][c] == 1:
                                # print('풋매도 재고있음')
                                put_my_have_str = '3011'
                    if put_my_have_str == '3011':
                        # 매도재고 : 매수신호 => 선물매수(풋매수 청산)
                        # 종목코드와 수량 (텍스트에서 읽어오기)
                        item_list_cnt = self.today_put_order_list_text_pickup()
                        # {'code_no': ['301S2410', '301S2400', '301S2380'], 'cnt': [1, 2, 2]}
                        # print(item_list_cnt)
                        # 청산은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            # 선물매수/풋청산
                            for have in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][have][:3] == '301':
                                    if self.option_myhave['sell_or_buy'][have] == 1:
                                        for i in range(len(item_list_cnt['code_no'])):
                                            if self.option_myhave['code'][have] == item_list_cnt['code_no'][i]:
                                                if self.option_myhave['myhave_cnt'][have] >= item_list_cnt['cnt'][i]:
                                                    item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                                                    item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i])
                                                    item_list_cnt_type['sell_buy_type'].append(2)
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
                        if myhave_buy_total_mall_basket_cnt_remove >= 4:
                            # 매수재고 : 매수신호 => 선물매수 건수가 바스켓 기준으로 4이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                            self.printt('(4)선물매수 건수가 바스켓 기준으로 4이상이면 거래없음')
                            # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                            option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                          self.buy_second_price[0])
                            self.printt('self.futrue_s_data[run_price][0]')
                            self.printt(self.futrue_s_data['run_price'][0])
                            self.printt('self.buy_second_price[0]')
                            self.printt(self.buy_second_price[0])
                            self.printt('option_s_sell_buy_point')
                            self.printt(option_s_sell_buy_point)
                            # option_s_sell_buy_point 텍스트 저장
                            self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                            # 연결선물가상매매
                            SellBuyType = '매수'
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            time_msg = ' 연결선물가상매매 : ' + text_time
                            # 텍스트 저장 호출
                            self.printt_buyed(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                            return
                        elif (myhave_buy_total_mall_basket_cnt_remove == 3) or (
                                myhave_buy_total_mall_basket_cnt_remove == 2):
                            # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                            option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                          self.buy_second_price[0])
                            self.printt('self.futrue_s_data[run_price][0]')
                            self.printt(self.futrue_s_data['run_price'][0])
                            self.printt('self.buy_second_price[0]')
                            self.printt(self.buy_second_price[0])
                            self.printt('option_s_sell_buy_point')
                            self.printt(option_s_sell_buy_point)
                            # option_s_sell_buy_point 텍스트 저장
                            self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                            # 옵션 종목검색(콜매도)
                            put_or_call = 'call'
                            if day_residue_int > 2:
                                month_mall_type = 'center_index'
                                # center_index / center_index_45
                            else:
                                month_mall_type = 'center_index_45'
                                # center_index / center_index_45
                            item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                            # print(item_list_cnt)
                            # item_list_cnt = {'code_no': ['201SA307'], 'cnt': [3]}   # 텍스트 읽은 결과값
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_type['sell_buy_type'].append(1)
                            self.printt('(3~2)옵션 종목검색(콜매도)')
                            self.printt(item_list_cnt_type)
                            # 텍스트 저장은 종목이 있을경우에만
                            if len(item_list_cnt['code_no']) > 0:
                                item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                                for i in range(len(item_list_cnt['code_no'])):
                                    item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                # 종목코드와 수량(텍스트에 저장하기)
                                self.today_call_order_list_text_store(item_list_cnt_for_store)
                        elif myhave_buy_total_mall_basket_cnt_remove == 1:
                            # 일반 진입
                            self.printt('(1)일반 진입')
                            pass

                        # 선물매수
                        item_list_cnt_type['code_no'].append(self.futrue_s_data['item_code'][0])
                        item_list_cnt_type['cnt'].append(basket_cnt)
                        item_list_cnt_type['sell_buy_type'].append(2)
                        # print(item_list_cnt_type)
                    elif future_s_day_residue_int <= (buy_roll_over_check_cnt + 2):
                        self.printt('차월물 진입')

                        # 선물재고 건수 및 옵션재고 확인
                        if myhave_buy_total_mall_basket_cnt_remove >= 4:
                            # 매수재고 : 매수신호 => 선물매수 건수가 바스켓 기준으로 4이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                            self.printt('(4)선물매수 건수가 바스켓 기준으로 4이상이면 거래없음')
                            # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                            option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                          self.buy_second_price[0])
                            self.printt('self.futrue_s_data[run_price][0]')
                            self.printt(self.futrue_s_data['run_price'][0])
                            self.printt('self.buy_second_price[0]')
                            self.printt(self.buy_second_price[0])
                            self.printt('option_s_sell_buy_point')
                            self.printt(option_s_sell_buy_point)
                            # option_s_sell_buy_point 텍스트 저장
                            self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                            # 연결선물가상매매
                            SellBuyType = '매수'
                            # 시분초
                            current_time = QTime.currentTime()
                            text_time = current_time.toString('hh:mm:ss')
                            time_msg = ' 연결선물가상매매 : ' + text_time
                            # 텍스트 저장 호출
                            self.printt_buyed(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                            return
                        elif (myhave_buy_total_mall_basket_cnt_remove == 3) or (
                                myhave_buy_total_mall_basket_cnt_remove == 2):
                            # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                            option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                          self.buy_second_price[0])
                            self.printt('self.futrue_s_data[run_price][0]')
                            self.printt(self.futrue_s_data['run_price'][0])
                            self.printt('self.buy_second_price[0]')
                            self.printt(self.buy_second_price[0])
                            self.printt('option_s_sell_buy_point')
                            self.printt(option_s_sell_buy_point)
                            # option_s_sell_buy_point 텍스트 저장
                            self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                            # 옵션 종목검색(콜매도)
                            put_or_call = 'call'
                            if day_residue_int > 2:
                                month_mall_type = 'center_index'
                                # center_index / center_index_45
                            else:
                                month_mall_type = 'center_index_45'
                                # center_index / center_index_45
                            item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                            # print(item_list_cnt)
                            # item_list_cnt = {'code_no': ['201SA307'], 'cnt': [3]}   # 텍스트 읽은 결과값
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                item_list_cnt_type['sell_buy_type'].append(1)
                            self.printt('(3~2)옵션 종목검색(콜매도)')
                            self.printt(item_list_cnt_type)
                            # 텍스트 저장은 종목이 있을경우에만
                            if len(item_list_cnt['code_no']) > 0:
                                item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                                for i in range(len(item_list_cnt['code_no'])):
                                    item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][i])
                                    item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                                # 종목코드와 수량(텍스트에 저장하기)
                                self.today_call_order_list_text_store(item_list_cnt_for_store)
                        elif myhave_buy_total_mall_basket_cnt_remove == 1:
                            # 일반 진입
                            self.printt('(1)일반 진입')
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
                # 재고수량 (매도/ 매수) 비교
                if myhave_sell_total_mall_cnt > 0:
                    self.printt('매도재고 있음')
                    self.printt('차월물만 진입')

                    # 선물재고 건수 및 옵션재고 확인
                    if myhave_sell_total_mall_basket_cnt_remove >= 4:
                        # 매도재고 : 매도신호 => 선물매도 건수가 바스켓 기준으로 4이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                        self.printt('(4)선물매도 건수가 바스켓 기준으로 4이상이면 거래없음')
                        # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                      self.sell_second_price[0])
                        self.printt('self.futrue_s_data[run_price][0]')
                        self.printt(self.futrue_s_data['run_price'][0])
                        self.printt('self.sell_second_price[0]')
                        self.printt(self.sell_second_price[0])
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)
                        # option_s_sell_buy_point 텍스트 저장
                        self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                        # 연결선물가상매매
                        SellBuyType = '매도'
                        # 시분초
                        current_time = QTime.currentTime()
                        text_time = current_time.toString('hh:mm:ss')
                        time_msg = ' 연결선물가상매매 : ' + text_time
                        # 텍스트 저장 호출
                        self.printt_selled(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                        return
                    elif (myhave_sell_total_mall_basket_cnt_remove == 3) or (
                            myhave_sell_total_mall_basket_cnt_remove == 2):
                        # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                      self.sell_second_price[0])
                        self.printt('self.futrue_s_data[run_price][0]')
                        self.printt(self.futrue_s_data['run_price'][0])
                        self.printt('self.sell_second_price[0]')
                        self.printt(self.sell_second_price[0])
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)
                        # option_s_sell_buy_point 텍스트 저장
                        self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                        # 옵션 종목검색(풋매도)
                        put_or_call = 'put'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)
                        # item_list_cnt = {'code_no': ['301SA307'], 'cnt': [3]}   # 텍스트 읽은 결과값
                        for i in range(len(item_list_cnt['code_no'])):
                            item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                            item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                            item_list_cnt_type['sell_buy_type'].append(1)
                        self.printt('(3~2)옵션 종목검색(풋매도)')
                        self.printt(item_list_cnt_type)
                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_put_order_list_text_store(item_list_cnt_for_store)
                    elif myhave_sell_total_mall_basket_cnt_remove == 1:
                        # 일반 진입
                        self.printt('(1)일반 진입')
                        pass

                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
                    # print(item_list_cnt_type)

                elif myhave_buy_total_mall_cnt > 0:
                    self.printt('매수재고 있음')
                    self.printt('차월물만 청산')

                    # 조건확인
                    # 콜재고 있을때
                    call_my_have_str = ''
                    for p in range(len(self.option_myhave['code'])):
                        # print(self.option_myhave['code'][p][:3])
                        if self.option_myhave['code'][p][:3] == '201':
                            call_my_have_str = '201'
                            # 매도
                            if self.option_myhave['sell_or_buy'][p] == 1:
                                # print('콜매도 재고있음')
                                call_my_have_str = '2011'
                    if call_my_have_str == '2011':
                        # 매수재고 : 매도신호 => 선물매도(콜매수 청산)
                        # 종목코드와 수량 (텍스트에서 읽어오기)
                        item_list_cnt = self.today_call_order_list_text_pickup()
                        # {'code_no': ['201S2410', '201S2400', '201S2380'], 'cnt': [1, 2, 2]}
                        # 청산은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            # 선물매도/풋청산
                            for have in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][have][:3] == '201':
                                    if self.option_myhave['sell_or_buy'][have] == 1:
                                        for i in range(len(item_list_cnt['code_no'])):
                                            if self.option_myhave['code'][have] == item_list_cnt['code_no'][i]:
                                                if self.option_myhave['myhave_cnt'][have] >= item_list_cnt['cnt'][i]:
                                                    item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                                                    item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i])
                                                    item_list_cnt_type['sell_buy_type'].append(2)
                    # 선물매도
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(1)
                    # print(item_list_cnt_type)
            # 신호확인은 당월물로
            elif self.futrue_s_data['run_price'][0] < day_poly_min_price:
                self.printt('차월물만 재고있음 선물매수(2) 신호발생')
                # 재고수량 (매도/ 매수) 비교
                if myhave_sell_total_mall_cnt > 0:
                    self.printt('매도재고 있음')
                    self.printt('차월물만 청산')

                    # 조건확인
                    # 풋재고 있을때
                    put_my_have_str = ''
                    for c in range(len(self.option_myhave['code'])):
                        # print(self.option_myhave['code'][c][:3])
                        if self.option_myhave['code'][c][:3] == '301':
                            put_my_have_str = '301'
                            # 매도
                            if self.option_myhave['sell_or_buy'][c] == 1:
                                # print('풋매도 재고있음')
                                put_my_have_str = '3011'
                    if put_my_have_str == '3011':
                        # 매도재고 : 매수신호 => 선물매수(풋매수 청산)
                        # 종목코드와 수량 (텍스트에서 읽어오기)
                        item_list_cnt = self.today_put_order_list_text_pickup()
                        # {'code_no': ['301S2410', '301S2400', '301S2380'], 'cnt': [1, 2, 2]}
                        # print(item_list_cnt)
                        # 청산은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            # 선물매수/풋청산
                            for have in range(len(self.option_myhave['code'])):
                                if self.option_myhave['code'][have][:3] == '301':
                                    if self.option_myhave['sell_or_buy'][have] == 1:
                                        for i in range(len(item_list_cnt['code_no'])):
                                            if self.option_myhave['code'][have] == item_list_cnt['code_no'][i]:
                                                if self.option_myhave['myhave_cnt'][have] >= item_list_cnt['cnt'][i]:
                                                    item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                                                    item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i])
                                                    item_list_cnt_type['sell_buy_type'].append(2)
                    # 선물매수
                    item_list_cnt_type['code_no'].append(self.futrue_s_data_45['item_code'][0])
                    item_list_cnt_type['cnt'].append(basket_cnt)
                    item_list_cnt_type['sell_buy_type'].append(2)
                    # print(item_list_cnt_type)

                elif myhave_buy_total_mall_cnt > 0:
                    self.printt('매수재고 있음')
                    self.printt('차월물만 진입')

                    # 선물재고 건수 및 옵션재고 확인
                    if myhave_buy_total_mall_basket_cnt_remove >= 4:
                        # 매수재고 : 매수신호 => 선물매수 건수가 바스켓 기준으로 4이상이면 거래없음(이론적인 거래는 실행되는 것으로 간주)
                        self.printt('(4)선물매수 건수가 바스켓 기준으로 4이상이면 거래없음')
                        # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                      self.buy_second_price[0])
                        self.printt('self.futrue_s_data[run_price][0]')
                        self.printt(self.futrue_s_data['run_price'][0])
                        self.printt('self.buy_second_price[0]')
                        self.printt(self.buy_second_price[0])
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)
                        # option_s_sell_buy_point 텍스트 저장
                        self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                        # 연결선물가상매매
                        SellBuyType = '매수'
                        # 시분초
                        current_time = QTime.currentTime()
                        text_time = current_time.toString('hh:mm:ss')
                        time_msg = ' 연결선물가상매매 : ' + text_time
                        # 텍스트 저장 호출
                        self.printt_buyed(Chain_Future_s_Item_Code[0] + '::(' + SellBuyType + time_msg + ')')
                        return
                    elif (myhave_buy_total_mall_basket_cnt_remove == 3) or (
                            myhave_buy_total_mall_basket_cnt_remove == 2):
                        # 지난진입 금액확인 :: 옵션매수 포인트 구하기(시뮬레이터 연속되는 +- 2 max금액)
                        option_s_sell_buy_point = abs(self.futrue_s_data['run_price'][0] -
                                                      self.buy_second_price[0])
                        self.printt('self.futrue_s_data[run_price][0]')
                        self.printt(self.futrue_s_data['run_price'][0])
                        self.printt('self.buy_second_price[0]')
                        self.printt(self.buy_second_price[0])
                        self.printt('option_s_sell_buy_point')
                        self.printt(option_s_sell_buy_point)
                        # option_s_sell_buy_point 텍스트 저장
                        self.option_s_sell_buy_point_store_fn(option_s_sell_buy_point)

                        # 옵션 종목검색(콜매도)
                        put_or_call = 'call'
                        if day_residue_int > 2:
                            month_mall_type = 'center_index'
                            # center_index / center_index_45
                        else:
                            month_mall_type = 'center_index_45'
                            # center_index / center_index_45
                        item_list_cnt = self.option_items_search(option_s_sell_buy_point, put_or_call, month_mall_type, basket_cnt)
                        # print(item_list_cnt)
                        # item_list_cnt = {'code_no': ['201SA307'], 'cnt': [3]}   # 텍스트 읽은 결과값
                        for i in range(len(item_list_cnt['code_no'])):
                            item_list_cnt_type['code_no'].append(item_list_cnt['code_no'][i])
                            item_list_cnt_type['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                            item_list_cnt_type['sell_buy_type'].append(1)
                        self.printt('(3~2)옵션 종목검색(콜매도)')
                        self.printt(item_list_cnt_type)
                        # 텍스트 저장은 종목이 있을경우에만
                        if len(item_list_cnt['code_no']) > 0:
                            item_list_cnt_for_store = {'code_no': [], 'cnt': []}
                            for i in range(len(item_list_cnt['code_no'])):
                                item_list_cnt_for_store['code_no'].append(item_list_cnt['code_no'][i])
                                item_list_cnt_for_store['cnt'].append(item_list_cnt['cnt'][i] * basket_cnt)
                            # 종목코드와 수량(텍스트에 저장하기)
                            self.today_call_order_list_text_store(item_list_cnt_for_store)
                    elif myhave_buy_total_mall_basket_cnt_remove == 1:
                        # 일반 진입
                        self.printt('(1)일반 진입')
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
            self.printt(basket_cnt)
            # basket_cnt 텍스트 저장
            self.future_s_basket_cnt_text_store(basket_cnt)
            # 바스켓 재설정

            # 신규진입
            # # 월봉 3차원 기울기 하향중
            # if future_s_month_poly_gradient == 'sell_time':
            if self.futrue_s_data['run_price'][0] > day_poly_max_price:
                self.printt('당월물 재고없음 선물매도(1)(신규진입)')
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
            # # 월봉 3차원 기울기 상향중
            # elif future_s_month_poly_gradient == 'buy_time':
            elif self.futrue_s_data['run_price'][0] < day_poly_min_price:
                self.printt('당월물 재고없음 선물매수(2)(신규진입)')
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
        self.printt('item_list_cnt_type')
        self.printt(item_list_cnt_type)

        # 검색된 종목코드 여부
        item_list_cnt = len(item_list_cnt_type['code_no'])
        if item_list_cnt > 0:
            self.future_s_market_sell_buy(item_list_cnt_type)

    # 선물 롤오버
    def future_s_roll_over_fn(self):
        # 당일날 선물 롤오버 있었거나 현재 주문중이면(혹시 옵션 롤오버 중 일경우를 대비하여) return
        if ((self.future_s_roll_over_run_var == True) or (self.progressBar_order.value() == 100)):
            return

        # 주문변수 초기화
        item_list_cnt_type = {'code_no': [], 'cnt': [], 'sell_buy_type': []}
        # 선물 바스켓 가져오기
        basket_cnt = self.future_s_basket_cnt_text_read()   #int
        # print(basket_cnt)
        # 선옵잔고요청 - 이벤트 슬롯
        self.myhave_option_rq()
        # # 예탁금및증거금조회 - 이벤트 슬롯
        # self.mymoney_option_rq()
        # 선물 영업일 기준 잔존일
        future_s_day_residue_int = self.futrue_s_data['day_residue'][0]  # int
        # print(future_s_day_residue_int)

        # 당일날 옵션 롤오버 없었을경우에만 실행
        if self.option_s_roll_over_run_var == False:
            # 이미 옵션 로오버 실행예정 변수 True 다시 실행 않하기
            self.option_s_roll_over_run_var = True
            # 옵션 롤오버
            day_residue_int = self.output_put_option_data['day_residue'][self.center_index]  # int
            # print(day_residue_int)
            # 옵션재고와 당월물 앞자리 5자리 코드가 같으면 롤오버 실행
            option_s_roll_over_run = False
            if day_residue_int <= 2:
                center_index_put_code_5dig = self.output_put_option_data['code'][self.center_index][:5]
                center_index_call_code_5dig = self.output_call_option_data['code'][self.center_index][:5]
                # print(center_index_put_code_5dig)
                # print(center_index_call_code_5dig)
                for m in range(len(self.option_myhave['code'])):
                    # 재고 확인
                    if self.option_myhave['code'][m][:5] == center_index_put_code_5dig:
                        option_s_roll_over_run = True
                    if self.option_myhave['code'][m][:5] == center_index_call_code_5dig:
                        option_s_roll_over_run = True
            if option_s_roll_over_run == True:
                # 중심가 변경시 옵션 튜닝 준비 = > 항상 현재에 맞춰서 <= 롤오버에도 활용
                self.printt('# 중심가 변경시 옵션 튜닝 준비 = > 항상 현재에 맞춰서 <= 롤오버에도 활용')
                self.option_s_center_index_change_ready()
                return

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
        self.printt(item_list_cnt_type)

        # 이미 로오버 처리했으면 변수 True 다시 실행 않하기
        self.future_s_roll_over_run_var = True
        # 검색된 종목코드 여부
        item_list_cnt = len(item_list_cnt_type['code_no'])
        if item_list_cnt >= 1:
            self.future_s_market_sell_buy(item_list_cnt_type)

    # 주식매수 준비
    def stock_buy_ready_fn(self, store_time_var):
        # 당일 매도 종목 찾기
        self.selled_today_items = self.selled_today_items_search_fn()
        self.printt('# 당일 매도 종목 찾기')
        self.printt(self.selled_today_items)

        # 당일 매수 종목 찾기
        self.buyed_today_items = self.buyed_today_items_search_fn()
        self.printt('# 당일 매수 종목 찾기')
        self.printt(self.buyed_today_items)

        # 기초종목 텍스트에서 읽기
        self.favorites_item_list = []
        self.favorites_item_list_percent = []
        # 선택종목 전체종목 txt 호출
        self.txt_pickup_for_choice_stock()
        self.printt('# self.favorites_item_list')
        self.printt(self.favorites_item_list)
        self.printt(self.favorites_item_list_percent)

        # 매수건 전송 -> 접수 않된건 삭제하기
        self.in_buy_trans_without_input_fn(self.favorites_item_list)

        # 체결강도조회 - 이벤트 슬롯 - 관심종목 조회함수 활용(거래량, 매도호가, 매수호가, 체결강도)
        # 인스턴스 변수 선언
        self.stock_deal_power_reset_output()
        transCode = ''
        transCode_cnt = 0
        for code in self.favorites_item_list:
            # print(code)
            transCode = transCode + code + ';'
            transCode_cnt += 1
        self.deal_power_trans_fn(transCode, transCode_cnt)
        # self.printt('# self.deal_power_data')
        # self.printt(self.deal_power_data)

        # # 체결강도 DB
        # # db명 설정
        # db_name_favorites_item = 'favorites_item_list'
        # # 체결강도 DB 저장
        # stock_data_store(store_time_var, Folder_Name_DB_Store, db_name_favorites_item, self.deal_power_data)

        # 매수가능 % 종목 저장용
        buy_able_item_code = []
        for j in range(len(self.favorites_item_list)):
            each_down_percent = int(self.favorites_item_list_percent[j])
            # 매수가능 % 종목 저장용
            if each_down_percent < 15:
                buy_able_item_code.append(self.favorites_item_list[j])

        # 매수가능 종목 저장용
        deal_power_tarket_item_list = []
        # ai로 구한 매수가 적용하기
        # 월봉
        # 매도 기울기 상향중 체크
        stock_trend_line_of_ai_month_able = []
        stock_trend_line_of_ai_month_minuus = []
        stock_trend_line_of_ai_month_able_buy_able_item_code = []
        self.stock_trend_line_of_ai_month = self.stock_trend_line_of_ai_month_data_fn()
        if self.stock_trend_line_of_ai_month != None:
            for i in range(len(self.stock_trend_line_of_ai_month['stock_no'])):
                # 신규진입일때는 샹향중일때만 진입(월봉)
                if ((self.stock_trend_line_of_ai_month['poly_h_gradient'][i] > 0) and (
                        self.stock_trend_line_of_ai_month['poly_l_gradient'][i] > 0)):
                    if self.stock_trend_line_of_ai_month['stock_no'][i] not in stock_trend_line_of_ai_month_able:
                        stock_trend_line_of_ai_month_able.append(self.stock_trend_line_of_ai_month['stock_no'][i])

                    if self.stock_trend_line_of_ai_month['stock_no'][i] in buy_able_item_code:
                        if self.stock_trend_line_of_ai_month['stock_no'][i] not in stock_trend_line_of_ai_month_able_buy_able_item_code:
                            stock_trend_line_of_ai_month_able_buy_able_item_code.append(self.stock_trend_line_of_ai_month['stock_no'][i])

                elif ((self.stock_trend_line_of_ai_month['poly_h_gradient'][i] < 0) and (
                        self.stock_trend_line_of_ai_month['poly_l_gradient'][i] < 0)):
                    if self.stock_trend_line_of_ai_month['stock_no'][i] not in stock_trend_line_of_ai_month_minuus:
                        stock_trend_line_of_ai_month_minuus.append(self.stock_trend_line_of_ai_month['stock_no'][i])

                # 연결선물
                if Chain_Future_s_Item_Code[0] == self.stock_trend_line_of_ai_month['stock_no'][i]:
                    # gui 하단에 표시
                    self.future_s_chain_trend_line_of_ai_month_h_str = str(
                        format(self.stock_trend_line_of_ai_month['poly_h_gradient'][i], '.2f'))
                    self.future_s_chain_trend_line_of_ai_month_l_str = str(
                        format(self.stock_trend_line_of_ai_month['poly_l_gradient'][i], '.2f'))
            # gui 하단에 표시
            self.trend_line_of_ai_month_total_cnt_str = str(len(self.stock_trend_line_of_ai_month['stock_no']))
            self.trend_line_of_ai_month_plus_cnt_str = str(len(stock_trend_line_of_ai_month_able))
            self.trend_line_of_ai_month_minus_cnt_str = str(len(stock_trend_line_of_ai_month_minuus))

        self.printt('stock_trend_line_of_ai_month_able')
        self.printt(len(stock_trend_line_of_ai_month_able))
        self.printt(stock_trend_line_of_ai_month_able)

        self.printt('stock_trend_line_of_ai_month_able_buy_able_item_code')
        self.printt(len(stock_trend_line_of_ai_month_able_buy_able_item_code))
        self.printt(stock_trend_line_of_ai_month_able_buy_able_item_code)

        self.stock_trend_line_of_ai_day = self.stock_trend_line_of_ai_day_data_fn()
        # self.printt('# self.stock_trend_line_of_ai_day')
        # self.printt(self.stock_trend_line_of_ai_day)
        # ai로 구한 값 있을때만 실행
        if self.stock_trend_line_of_ai_day != None:
            for i in range(len(self.stock_trend_line_of_ai_day['stock_no'])):
                for k in range(len(self.deal_power_data['stock_no'])):
                    if self.stock_trend_line_of_ai_day['stock_no'][i] == self.deal_power_data['stock_no'][k]:
                        each_run_price = self.deal_power_data['run_price'][k]
                        each_buy_min_price = self.stock_trend_line_of_ai_day['poly_buy_min_price'][i]
                        if each_buy_min_price >= each_run_price:

                            # 보유종목 여부 판단하여 있으면 무조건 매수, 아니면 추세선 모두 샹향중일때만 진입
                            if self.stock_trend_line_of_ai_day['stock_no'][i] in self.stock_have_data['stock_no']:
                                # print('보유종목 있음')
                                deal_power_tarket_item_list.append(self.stock_trend_line_of_ai_day['stock_no'][i])
                            else:
                                # 2021년 01월 19일 :: 3차원 그래프의 기울기가 모두 (+)일때만 진입(신규여부 상관없이)
                                # <= 2021년 03월 29일 월봉 기울기 추가하면서 제외
                                # 신규진입일때는 샹향중일때만 진입(월봉)
                                if self.stock_trend_line_of_ai_day['stock_no'][i] in stock_trend_line_of_ai_month_able:
                                    # # 신규진입일때는 샹향중일때만 진입(일봉)
                                    # if ((self.stock_trend_line_of_ai_day['poly_h_gradient'][i] > 0) and (
                                    #         self.stock_trend_line_of_ai_day['poly_l_gradient'][i] > 0)):
                                    # 매수가능 종목 저장용
                                    if self.stock_trend_line_of_ai_day['stock_no'][i] in buy_able_item_code:
                                        deal_power_tarket_item_list.append(self.stock_trend_line_of_ai_day['stock_no'][i])

                    # 연결선물
                    if Chain_Future_s_Item_Code[0] == self.stock_trend_line_of_ai_day['stock_no'][i]:
                        # gui 하단에 표시
                        self.future_s_chain_trend_line_of_ai_day_h_str = str(format(self.stock_trend_line_of_ai_day['poly_h_gradient'][i], '.2f'))
                        self.future_s_chain_trend_line_of_ai_day_l_str = str(format(self.stock_trend_line_of_ai_day['poly_l_gradient'][i], '.2f'))
                        self.future_s_chain_day_poly_max_price_str = str(format(self.stock_trend_line_of_ai_day['poly_sell_max_price'][i], '.2f'))
                        self.future_s_chain_day_poly_min_price_str = str(format(self.stock_trend_line_of_ai_day['poly_buy_min_price'][i], '.2f'))

        # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
        # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
        self.future_s_simul_of_trend_line_day = self.future_s_simul_of_trend_line_day_data_fn()
        # self.printt('# self.future_s_simul_of_trend_line_day')
        # self.printt(self.future_s_simul_of_trend_line_day)
        # 시뮬레이터 구한 값 있을때만 실행
        sell_mode_cnt = 0
        buy_mode_cnt = 0
        self.sell_second_price = []
        self.buy_second_price = []
        if self.future_s_simul_of_trend_line_day != None:
            # sell_second_price = 2
            for i in range(len(self.future_s_simul_of_trend_line_day['deal_day'])):
                # mode 더해보기(+-)
                sell_mode_cnt = sell_mode_cnt + self.future_s_simul_of_trend_line_day['sell_mode'][i] - self.future_s_simul_of_trend_line_day['buy_mode'][i]
                buy_mode_cnt = buy_mode_cnt + self.future_s_simul_of_trend_line_day['buy_mode'][i] - self.future_s_simul_of_trend_line_day['sell_mode'][i]
                if sell_mode_cnt == 2:
                    self.sell_second_price.append(self.future_s_simul_of_trend_line_day['poly_sell_max_price'][i])
                if buy_mode_cnt == 2:
                    self.buy_second_price.append(self.future_s_simul_of_trend_line_day['poly_buy_min_price'][i])
        # [313.97624597998293, 319.3358123569823, 328.04294093755414, 327.4622603066631, 330.33129653359316]
        # [327.8975806465704, 340.01125168186525, 343.00473614867394, 341.4551787222071, 339.87645281536874]
        # print(self.sell_second_price)
        # print(self.buy_second_price)

        self.printt('# deal_power_tarket_item_list')
        self.printt(len(deal_power_tarket_item_list))
        self.printt(deal_power_tarket_item_list)

        # 계좌잔고 시세요청
        self.stock_have_data_rq()
        # # 테이블 위젯에 표시하기
        # self.stock_listed_slot(self.stock_have_data)
        # 서버에서 수신받은 stock_data
        self.printt('# 서버에서 수신받은 stock_data')
        self.printt(len(self.stock_have_data['stock_no']))
        self.printt(self.stock_have_data)

        # 추정예탁자산/총평가금액
        self.printt('# 추정예탁자산 :: only stock(전체자신의 2/12 수동으로 수시로 맞추기)')   #  :: 202209 전략수정 (자산배정 참조)
        self.printt(format(self.estimated_deposit, ','))
        self.printt('# 총평가금액')
        self.printt(format(self.total_eval_price, ','))

        # # '추정예탁자산'을 선물옵션 예탁금과 합하여
        # future_s_option_s_stock_s_total_money = int(self.option_have_money + self.estimated_deposit)
        # self.printt('future_s_option_s_stock_s_total_money')
        # self.printt(format(future_s_option_s_stock_s_total_money, ','))
        # total_estimated_deposit = int(future_s_option_s_stock_s_total_money / 2)
        # print('total_estimated_deposit')
        # print(format(total_estimated_deposit, ','))

        # 총평가금액
        # self.total_eval_price
        # 주문가능 금액 = 추정예탁자산 - 총평가금액
        self.buy_able_money = int(self.estimated_deposit - self.total_eval_price)
        self.printt('self.buy_able_money')
        self.printt(format(self.buy_able_money, ','))

        # 1회 stock 투입금액 ::=> 20220610 :: 추정예탁자산(self.estimated_deposit)의 10%로 결정
        self.market_in_percent_won = int(self.estimated_deposit * (Market_In_Percent / 100))
        self.printt('self.market_in_percent_won')
        self.printt(format(self.market_in_percent_won, ','))

        # 선물 변화 건수 체크
        future_s_change_cnt = len(self.future_s_change_listed_var)
        # 선물 변화 건수 체크
        if future_s_change_cnt >= 2:
            # 자동주문 버튼 True 주문실행
            if self.auto_order_button_var == True:
                # 주식매수 종목검색
                self.stock_buy_items_search(deal_power_tarket_item_list, self.deal_power_data, self.buyed_today_items)

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
        con.close()
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

        return stock_trend_line_of_ai_month

    # 일봉
    # 매도 최고가 / 매수 최고가 / 기울기 구하기
    def stock_trend_line_of_ai_day_data_fn(self):
        # 매도 최고가 / 매수 최고가 / 기울기 구하기
        stock_trend_line_of_ai_day = {'stock_no': [],
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
        db_name = 'stock_trend_line_of_ai_day' + '.db'
        # print(db_name)
        db_name_db = db_file_path + '/' + db_name
        # print(db_name_db)

        # 테이블명 가져오기
        con = sqlite3.connect(db_name_db)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name = cursor.fetchall()
        con.close()
        # print(total_table_name)
        if len(total_table_name) == 0:
            return

        table_name_list = []
        # 가장 최근일자 1건만 취하기
        table_name_list.append(total_table_name[-1][0])
        self.printt('stock_trend_line_of_ai_day 가장 최근 테이블')
        self.printt(table_name_list)
        # print('stock_trend_line_of_ai_day 가장 최근 테이블')
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
                stock_trend_line_of_ai_day['stock_no'].append(stock_no[i])
                stock_trend_line_of_ai_day['poly_sell_max_price'].append(poly_sell_max_price[i])
                stock_trend_line_of_ai_day['poly_buy_min_price'].append(poly_buy_min_price[i])
                stock_trend_line_of_ai_day['sell_max_price'].append(sell_max_price[i])
                stock_trend_line_of_ai_day['buy_min_price'].append(buy_min_price[i])
                stock_trend_line_of_ai_day['poly_h_gradient'].append(poly_h_gradient[i])
                stock_trend_line_of_ai_day['poly_l_gradient'].append(poly_l_gradient[i])
                stock_trend_line_of_ai_day['h_gradient'].append(h_gradient[i])
                stock_trend_line_of_ai_day['l_gradient'].append(l_gradient[i])
        # print(stock_trend_line_of_ai_day)

        return stock_trend_line_of_ai_day

    # 일봉 시뮬레이터
    # future_s_simul_of_trend_line_day 데이타 미리 가져다 놓기
    def future_s_simul_of_trend_line_day_data_fn(self):
        # 일봉 시뮬레이터 자료
        future_s_simul_of_trend_line_day = {'deal_day': [],
                                  'running_y_h': [], 'running_y_l': [],
                                  'sell_mode': [], 'buy_mode': [],
                                  'poly_h_gradient': [], 'poly_l_gradient': [],
                                  'poly_sell_max_price': [], 'poly_buy_min_price': []}
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
        db_name = 'future_s_simul_of_trend_line_day' + '.db'
        # print(db_name)
        db_name_db = db_file_path + '/' + db_name
        # print(db_name_db)

        # 테이블명 가져오기
        con = sqlite3.connect(db_name_db)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name = cursor.fetchall()
        con.close()
        # print(total_table_name)
        if len(total_table_name) == 0:
            return

        table_name_list = []
        # 가장 최근일자 1건만 취하기
        table_name_list.append(total_table_name[-1][0])
        self.printt('future_s_simul_of_trend_line_day 가장 최근 테이블')
        self.printt(table_name_list)
        # print('stock_trend_line_of_ai_day 가장 최근 테이블')
        # print(table_name_list)

        # 데이타 가져오기 함수 호출
        for table_name in table_name_list:
            data_pickup_ret = data_pickup(db_name_db, table_name)
            # print(table_name)
            # print(data_pickup_ret)
            deal_day = data_pickup_ret['deal_day'].values
            running_y_h = data_pickup_ret['running_y_h'].values
            running_y_l = data_pickup_ret['running_y_l'].values
            sell_mode = data_pickup_ret['sell_mode'].values
            buy_mode = data_pickup_ret['buy_mode'].values
            poly_h_gradient = data_pickup_ret['poly_h_gradient'].values
            poly_l_gradient = data_pickup_ret['poly_l_gradient'].values
            poly_sell_max_price = data_pickup_ret['poly_sell_max_price'].values
            poly_buy_min_price = data_pickup_ret['poly_buy_min_price'].values

            for i in range(len(deal_day)):
                # 테이타 생성
                future_s_simul_of_trend_line_day['deal_day'].append(deal_day[i])
                future_s_simul_of_trend_line_day['running_y_h'].append(running_y_h[i])
                future_s_simul_of_trend_line_day['running_y_l'].append(running_y_l[i])
                future_s_simul_of_trend_line_day['sell_mode'].append(sell_mode[i])
                future_s_simul_of_trend_line_day['buy_mode'].append(buy_mode[i])
                future_s_simul_of_trend_line_day['poly_h_gradient'].append(poly_h_gradient[i])
                future_s_simul_of_trend_line_day['poly_l_gradient'].append(poly_l_gradient[i])
                future_s_simul_of_trend_line_day['poly_sell_max_price'].append(poly_sell_max_price[i])
                future_s_simul_of_trend_line_day['poly_buy_min_price'].append(poly_buy_min_price[i])
        # print(future_s_simul_of_trend_line_day)

        return future_s_simul_of_trend_line_day

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
        con.close()
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

    # 매수건 전송 -> 접수 않된건 삭제하기
    def in_buy_trans_without_input_fn(self, favorites_item_list):
        # 매수건 전송 -> 접수 않됨건 삭제하기
        # 주문 전송 결과에서
        # 삭제코드 리스트
        del_code_list = []
        for i in range(len(self.order_trans_var_stock['modify_item'])):
            # 전송
            # 매수이고
            if self.order_trans_var_stock['SellBuyType'][i] == 2:
                # 체결강도 전체리스트에 있는가 확인
                if self.order_trans_var_stock['modify_item'][i] in favorites_item_list:
                    # 접수
                    # 접수 SellBuyType 0이면
                    if self.order_input_var_stock['SellBuyType'][i] == 0:
                        # 접수 modify_item 공백이면
                        if self.order_input_var_stock['modify_item'][i] == '':
                            del_code_list.append(i)
        # 꺼꾸로 지운다
        for i in range(len(self.order_trans_var_stock['modify_item']) - 1, -1, -1):
            for j in range(len(del_code_list)):
                # 삭제코드 리스트와 인덱스가 같으면 삭제한다
                if i == del_code_list[j]:

                    self.printt('# 매수건 전송 -> 접수 않된건 삭제')
                    self.printt(self.order_trans_var_stock['OrderRunKind'][i])

                    # 주문 전송 결과
                    del self.order_trans_var_stock['OrderRunKind'][i]
                    del self.order_trans_var_stock['SellBuyType'][i]
                    del self.order_trans_var_stock['OrderRunCode'][i]
                    del self.order_trans_var_stock['OrderRunVolume'][i]
                    del self.order_trans_var_stock['OrderRunPrice'][i]
                    del self.order_trans_var_stock['OrgOrderNo'][i]
                    del self.order_trans_var_stock['modify_item'][i]
                    # 주문 접수 결과
                    del self.order_input_var_stock['OrderRunKind'][i]
                    del self.order_input_var_stock['SellBuyType'][i]
                    del self.order_input_var_stock['OrderRunCode'][i]
                    del self.order_input_var_stock['OrderRunVolume'][i]
                    del self.order_input_var_stock['OrderRunPrice'][i]
                    del self.order_input_var_stock['OrgOrderNo'][i]
                    del self.order_input_var_stock['modify_item'][i]
                    # 주문 실행 결과
                    del self.order_result_var_stock['OrderRunKind'][i]
                    del self.order_result_var_stock['SellBuyType'][i]
                    del self.order_result_var_stock['OrderRunCode'][i]
                    del self.order_result_var_stock['OrderRunVolume'][i]
                    del self.order_result_var_stock['OrderRunPrice'][i]
                    del self.order_result_var_stock['OrgOrderNo'][i]
                    del self.order_result_var_stock['modify_item'][i]

    # API에서 지난 월봉(30개월)간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
    # API에서 지난 30일간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
    def stock_shlc_store_for_ai_fn(self, current_today, choice_stock_filename, db_name_db_month, db_name_db_day):
        # 폴더구성
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
        for f in dir_list_files:
            if f.startswith(choice_stock_filename):
                choice_stock_list.append(f)
        print(choice_stock_list)
        # choice_stock 파일이 없으면 패스
        if len(choice_stock_list) == 0:
            return

        # 텍스트파일에서 종목데이타 저장하기
        stock_item_data = {'stock_item_no': [], 'stock_item_name': []}
        for file_name in choice_stock_list:
            choice_stock_file_path_name = choice_stock_files_path + '/' + file_name
            f = open(choice_stock_file_path_name, 'rt', encoding='UTF8')
            choice_stock_items = f.readlines()
            f.close()
            for choice_stock_item in choice_stock_items:
                item = choice_stock_item.split('::')
                # print(item)
                stock_item_data['stock_item_no'].append(item[2].strip('\n'))
                stock_item_data['stock_item_name'].append(item[0])
        print('stock_item_data')
        print(stock_item_data)
        print(len(stock_item_data['stock_item_no']))
        print(stock_item_data['stock_item_no'])

        # 테이블명 구하기
        # db_store 폴더
        is_store_folder = os.path.isdir(Folder_Name_DB_Store)
        if is_store_folder == False:
            return
        dir_list_year = os.listdir(Folder_Name_DB_Store)
        # print(dir_list_year)

        # print(current_year)
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        is_db_file = os.path.isdir(db_file_path)
        if is_db_file == False:
            os.makedirs(db_file_path)


        # 테이블명 가져오기
        con = sqlite3.connect(db_name_db_month)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name_of_db = cursor.fetchall()
        # print(total_table_name_of_db)
        # 실제 테이블 구하기
        total_table_name = []
        for table in total_table_name_of_db:
            total_table_name.append(table[0])
        print('total_table_name_of_db')
        print(total_table_name)
        # db테이블 삭제
        for table_name in total_table_name:
            # db테이블 삭제
            cursor.execute(
                "DROP TABLE '%s'" %
                table_name
            )
        print('월봉 db테이블 모두 삭제')

        ref_day = current_today
        end_day = current_today
        # print(ref_day)
        # 주식월봉차트조회요청
        for stock_code in stock_item_data['stock_item_no']:
            # stock_code = '035600'

            # 주식월봉차트조회요청
            self.stock_shlc_month_data_fn(stock_code, ref_day, end_day)
            # print(self.output_stock_shlc_month_data)

            # db테이블 생성
            cursor.execute(
                "CREATE TABLE '%s'(stock_date text, stock_start int, stock_high int, stock_low int, stock_end int, vol_cnt int)" % (
                    stock_code
                )
            )
            for d in range(len(self.output_stock_shlc_month_data['stock_date'])):

                cursor.execute(
                    "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s, %s)" % (
                        stock_code,
                        self.output_stock_shlc_month_data['stock_date'][d], self.output_stock_shlc_month_data['stock_start'][d],
                        self.output_stock_shlc_month_data['stock_high'][d], self.output_stock_shlc_month_data['stock_low'][d],
                        self.output_stock_shlc_month_data['stock_end'][d], self.output_stock_shlc_month_data['vol_cnt'][d]
                    )
                )
        # db닫기
        con.commit()
        con.close()
        # print("Sleep 60 seconds from now on...")
        # time.sleep(60)

        # 주식일봉차트조회요청
        # 테이블명 가져오기
        con = sqlite3.connect(db_name_db_day)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name_of_db = cursor.fetchall()
        # print(total_table_name_of_db)
        # 실제 테이블 구하기
        total_table_name = []
        for table in total_table_name_of_db:
            total_table_name.append(table[0])
        print('total_table_name_of_db')
        print(total_table_name)
        # db테이블 삭제
        for table_name in total_table_name:
            # db테이블 삭제
            cursor.execute(
                "DROP TABLE '%s'" %
                table_name
            )
        print('일봉 db테이블 모두 삭제')

        # 주식일봉차트조회요청
        for stock_code in stock_item_data['stock_item_no']:
            # stock_code = '035600'
            # 주식일봉차트조회요청
            self.stock_shlc_data_fn(stock_code, current_today)
            # print(self.output_stock_shlc_data)

            # db테이블 생성
            cursor.execute(
                "CREATE TABLE '%s'(stock_date text, stock_start int, stock_high int, stock_low int, stock_end int, vol_cnt int)" % (
                    stock_code
                )
            )
            for d in range(len(self.output_stock_shlc_data['stock_date'])):

                cursor.execute(
                    "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s, %s)" % (
                        stock_code,
                        self.output_stock_shlc_data['stock_date'][d], self.output_stock_shlc_data['stock_start'][d],
                        self.output_stock_shlc_data['stock_high'][d], self.output_stock_shlc_data['stock_low'][d],
                        self.output_stock_shlc_data['stock_end'][d], self.output_stock_shlc_data['vol_cnt'][d]
                    )
                )
        # db닫기
        con.commit()
        con.close()
        # print("Sleep 60 seconds from now on...")
        # time.sleep(60)

        print('stock db테이블 모두 완료')

    # API에서 지난 월봉(30개월)간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
    # API에서 지난 30일간 시고저종 수신받아서 db에 저장(딥러닝 훈련용)
    def future_s_store_for_ai_fn(self, current_today, choice_chain_future_s_item_code, db_name_db_month, db_name_db_day):
        # 테이블명 구하기
        # db_store 폴더
        db_file_path = os.getcwd() + '/' + Folder_Name_DB_Store
        is_db_file = os.path.isdir(db_file_path)
        if is_db_file == False:
            os.makedirs(db_file_path)

        # 테이블명 가져오기
        con = sqlite3.connect(db_name_db_month)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name_of_db = cursor.fetchall()
        # print(total_table_name_of_db)
        # 실제 테이블 구하기
        total_table_name = []
        for table in total_table_name_of_db:
            total_table_name.append(table[0])
        print('total_table_name_of_db')
        print(total_table_name)
        # db테이블 삭제
        for table_name in total_table_name:
            # db테이블 삭제
            cursor.execute(
                "DROP TABLE '%s'" %
                table_name
            )
        print('월봉 db테이블 모두 삭제')

        # 선물월차트요청
        for future_s_code in choice_chain_future_s_item_code:
            # future_s_code = '10100000'
            # print(future_s_code)

            # 선물월차트요청
            self.future_s_shlc_month_data_fn(future_s_code, current_today)

            # db테이블 생성
            cursor.execute(
                "CREATE TABLE '%s'(stock_date text, stock_start int, stock_high int, stock_low int, stock_end int, vol_cnt int)" % (
                    future_s_code
                )
            )
            for d in range(len(self.output_future_s_chain_shlc_month_data['future_s_date'])):

                cursor.execute(
                    "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s, %s)" % (
                        future_s_code,
                        self.output_future_s_chain_shlc_month_data['future_s_date'][d], self.output_future_s_chain_shlc_month_data['future_s_start'][d],
                        self.output_future_s_chain_shlc_month_data['future_s_high'][d], self.output_future_s_chain_shlc_month_data['future_s_low'][d],
                        self.output_future_s_chain_shlc_month_data['future_s_end'][d], self.output_future_s_chain_shlc_month_data['vol_cnt'][d]
                    )
                )
        # db닫기
        con.commit()
        con.close()
        # print("Sleep 60 seconds from now on...")
        # time.sleep(60)


        # 테이블명 가져오기
        con = sqlite3.connect(db_name_db_day)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        total_table_name_of_db = cursor.fetchall()
        # print(total_table_name_of_db)
        # 실제 테이블 구하기
        total_table_name = []
        for table in total_table_name_of_db:
            total_table_name.append(table[0])
        print('total_table_name_of_db')
        print(total_table_name)
        # db테이블 삭제
        for table_name in total_table_name:
            # db테이블 삭제
            cursor.execute(
                "DROP TABLE '%s'" %
                table_name
            )
        print('일봉 db테이블 모두 삭제')

        # 선물옵션일차트요청
        for future_s_code in choice_chain_future_s_item_code:
            # future_s_code = '10100000'

            # 선물옵션일차트요청
            self.future_s_shlc_day_data_fn(future_s_code, current_today)

            # db테이블 생성
            cursor.execute(
                "CREATE TABLE '%s'(stock_date text, stock_start int, stock_high int, stock_low int, stock_end int)" % (
                    future_s_code
                )
            )
            for d in range(len(self.output_future_s_chain_shlc_day_data['future_s_date'])):

                cursor.execute(
                    "INSERT INTO '%s' VALUES('%s', '%s', '%s', '%s', %s)" % (
                        future_s_code,
                        self.output_future_s_chain_shlc_day_data['future_s_date'][d], self.output_future_s_chain_shlc_day_data['future_s_start'][d],
                        self.output_future_s_chain_shlc_day_data['future_s_high'][d], self.output_future_s_chain_shlc_day_data['future_s_low'][d],
                        self.output_future_s_chain_shlc_day_data['future_s_end'][d]
                    )
                )
        # db닫기
        con.commit()
        con.close()
        # print("Sleep 60 seconds from now on...")
        # time.sleep(60)

        print('future_s db테이블 모두 완료')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()
