import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

from dao import BuyInfo, BuyRecord, OrderInfo
from data_struct import to_json
from log import logger
from upload_lanzouyun import Uploader

local_save_path = "utils/user_monthly_pay_info.txt"

# 一个月的天数以31计算
month_inc = timedelta(days=31)


def update_buy_user_local(order_infos: List[OrderInfo]):
    buy_users = {}  # type: Dict[str, BuyInfo]
    if os.path.exists(local_save_path):
        with open(local_save_path, 'r', encoding='utf-8') as data_file:
            raw_infos = json.load(data_file)
            for qq, raw_info in raw_infos.items():
                info = BuyInfo().auto_update_config(raw_info)
                buy_users[qq] = info

    datetime_fmt = "%Y-%m-%d %H:%M:%S"
    now = datetime.now()
    now_str = now.strftime(datetime_fmt)

    for order_info in order_infos:
        if order_info.qq in buy_users:
            user_info = buy_users[order_info.qq]
        else:
            user_info = BuyInfo()
            user_info.qq = order_info.qq
            buy_users[order_info.qq] = user_info

        # 更新时长
        expired_at = datetime.strptime(user_info.expire_at, datetime_fmt)
        if now > expired_at:
            # 已过期，从当前时间开始重新计算
            start_time = now
        else:
            # 续期，从之前结束时间叠加
            start_time = expired_at
        updated_expired_at = start_time + order_info.buy_month * month_inc
        user_info.expire_at = updated_expired_at.strftime(datetime_fmt)

        user_info.total_buy_month += order_info.buy_month
        user_info.buy_records.append(BuyRecord().auto_update_config({
            "buy_month": order_info.buy_month,
            "buy_at": now_str,
        }))

        # 更新游戏QQ
        for game_qq in order_info.game_qqs:
            if game_qq not in user_info.game_qqs:
                user_info.game_qqs.append(game_qq)

        msg = f"{user_info.qq} 购买 {order_info.buy_month} 个月成功，过期时间为{user_info.expire_at}，购买前过期时间为{expired_at}。累计购买{user_info.total_buy_month}个月。"
        msg += "购买详情如下：\n" + '\n'.join('\t' + f'{record.buy_at} 购买{record.buy_month}月' for record in user_info.buy_records)
        logger.info(msg)

    with open(local_save_path, 'w', encoding='utf-8') as save_file:
        json.dump(to_json(buy_users), save_file, indent=2)


def upload():
    logger.info("开始上传到蓝奏云")
    with open("upload_cookie.json") as fp:
        cookie = json.load(fp)
    uploader = Uploader(cookie)
    if uploader.login_ok:
        logger.info("蓝奏云登录成功，开始更新付费名单")
        uploader.upload_to_lanzouyun(os.path.realpath(local_save_path), uploader.folder_online_files, uploader.user_monthly_pay_info_filename)
    else:
        logger.error("蓝奏云登录失败")


def process_orders(order_info: List[OrderInfo]):
    update_buy_user_local(order_infos)
    upload()


if __name__ == '__main__':
    raw_order_infos = [
        # QQ号   游戏QQ列表  购买月数
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
        # ("XXXXXXXX", [], 1),
    ]

    order_infos = []
    for qq, game_qqs, buy_month in raw_order_infos:
        order_info = OrderInfo()
        order_info.qq = qq
        order_info.game_qqs = game_qqs
        order_info.buy_month = buy_month
        order_infos.append(order_info)

    process_orders(order_infos)
