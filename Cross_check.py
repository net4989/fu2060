import sys
from PyQt5.QtWidgets import *





class Cross:
    def __init__(self, cmp_call, cmp_put):
        # 수신받은 콜/풋 최근 변경 데이터
        self.cmp_call = cmp_call
        self.cmp_put = cmp_put


    def cross_check(self):
        # 딕셔너리 변수 분리::차이(콜-풋)
        FirstValueVar = self.cmp_call[-1] - self.cmp_put[-1]
        SecondValueVar = self.cmp_call[-2] - self.cmp_put[-2]
        # 두 값의 비교값
        CompareValueVar = FirstValueVar * SecondValueVar
        # 현재값이 0이면 다음값에 의해서
        if FirstValueVar == 0:
            return 0
        # 현재값이 0이 아니면 비교변수와 지난값에 의해서
        elif (CompareValueVar < 0) or (SecondValueVar == 0):
            # 양수이면 콜승
            if FirstValueVar > 0:
                return 2
            # 음수이면 풋승
            elif FirstValueVar < 0:
                return 3

        # print(self.cmp_call[-2])
        # print(self.cmp_call[-1])
        # print(self.cmp_put)






            # current_cmp_price = self.cmp_call[up_down_index_str][-1] - self.cmp_put[up_down_index_str][-1]
            # before_cmp_price = self.cmp_call[up_down_index_str][-2] - self.cmp_put[up_down_index_str][-2]

            # 현재가 - 이전가
            # cmp_value = current_cmp_price * before_cmp_price
            # if current_cmp_price == 0:
            #     pass
            #
            # elif (cmp_value < 0) or (before_cmp_price == 0):
            #     if current_cmp_price > 0:
            #         pass
            #     elif current_cmp_price < 0:
            #         pass




if __name__ == "__main__":
    app = QApplication(sys.argv)
    up1_cross = Cross('201fff', 3)
    up1_cross.cross_check()