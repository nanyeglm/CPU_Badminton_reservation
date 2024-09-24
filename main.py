import requests
import json
from datetime import datetime, timedelta
import random
from faker import Faker
import tkinter as tk
from tkinter import messagebox, ttk, Toplevel, Checkbutton, IntVar
import threading

# 设置 Faker 实例，指定中文环境
fake = Faker('zh_CN')

# 目标 URL
url = "https://cgyy.xiaorankeji.com/index.php?s=/api/order/addByUid"

# 请求头
headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": "https://cgyy.xiaorankeji.com/h5/index.html",
}

# 定义常见中文符号与英文符号的对应关系
chinese_to_english_map = {
    '：': ':',
    '，': ',',
    '（': '(',
    '）': ')',
    '“': '"',
    '”': '"',
    '！': '!',
    '？': '?',
    '。': '.'
}

# 符号转换函数，将中文符号替换为英文符号
def convert_chinese_symbols(text):
    for chinese, english in chinese_to_english_map.items():
        text = text.replace(chinese, english)
    return text

# 定义全局的 gym_options 字典
gym_options = {}

# 从 API 获取 gym_options 数据
def fetch_gym_data(gym_ids):
    global gym_options
    for gym_id in gym_ids:
        gym_url = f"https://cgyy.xiaorankeji.com/index.php?s=/api/gym/detail&gymId={gym_id}"
        try:
            response = requests.get(gym_url)
            response.raise_for_status()
            data = response.json()
            if 'data' in data and 'detail' in data['data']:
                detail = data['data']['detail']
                gym_title = detail.get('title', '')
                category_id = detail.get('category_id', '')
                category_title = detail.get('category_title', '')  # Assuming API provides this
                store_id = detail.get('store_id', '')

                # 构建 place_mapping
                place_mapping = {}
                for place in detail.get('placeList', []):
                    place_title = place.get('title', '').replace('场地', '')
                    place_id = place.get('place_id', '')
                    place_mapping[place_title] = place_id

                # 构建 interval_mapping
                interval_mapping = []
                for interval in detail.get('intervalList', []):
                    interval_mapping.append({
                        "Interval ID": interval.get('interval_id', ''),
                        "Week Day": interval.get('week_day', ''),
                        "Start Time": interval.get('start_time', ''),
                        "End Time": interval.get('end_time', ''),
                        "is_reserve": interval.get('is_reserve', 1)
                    })

                gym_options[gym_title] = {
                    "gym_id": gym_id,
                    "gym_title": gym_title,
                    "category_id": category_id,
                    "category_title": category_title,
                    "store_id": store_id,
                    "place_mapping": place_mapping,
                    "interval_mapping": interval_mapping
                }
            else:
                messagebox.showerror("错误", f"无法获取场馆 {gym_id} 的数据。")
        except Exception as e:
            messagebox.showerror("错误", f"获取场馆 {gym_id} 数据失败：{e}")

# 预约功能
def submit_form():
    uid = convert_chinese_symbols(uid_entry.get())
    place_title_input = convert_chinese_symbols(place_title_entry.get())
    start_time = convert_chinese_symbols(start_time_entry.get())
    order_date = order_date_combobox.get()  # 从下拉框获取预约日期
    order_name = convert_chinese_symbols(order_name_entry.get())  # 获取用户输入的姓名
    order_phone = convert_chinese_symbols(order_phone_entry.get())  # 获取用户输入的电话
    gym_selection = gym_combobox.get()  # 获取用户选择的场馆

    # 必填项校验
    if not uid or not place_title_input or not start_time or not order_date or not gym_selection:
        messagebox.showerror("错误", "请填写所有必填项！")
        return

    # 获取场馆数据
    gym_data = gym_options.get(gym_selection)
    if not gym_data:
        messagebox.showerror("错误", "请选择有效的场馆！")
        return

    # 获取对应的 place_mapping 和 interval_mapping
    place_mapping = gym_data["place_mapping"]
    interval_mapping = gym_data["interval_mapping"]

    # 确保用户输入的场地号有效，并自动添加 "号"
    if not place_title_input.endswith("号"):
        if place_title_input.isdigit():
            place_title = place_title_input + "号"
        else:
            messagebox.showerror("错误", f"无效的场地号: {place_title_input}")
            return
    else:
        place_title = place_title_input  # 用户已经输入了“号”

    # 验证场地号是否在映射中
    if place_title not in place_mapping:
        messagebox.showerror("错误", f"无效的场地号: {place_title_input}")
        return

    # 如果姓名为空，使用 Faker 随机生成
    if not order_name:
        order_name = generate_random_chinese_name()

    # 如果电话号码为空，使用 Faker 随机生成
    if not order_phone:
        order_phone = generate_random_phone()

    # 计算结束时间
    end_time = calculate_end_time(start_time)

    # 获取 week_day
    week_day = get_week_day(order_date)

    # 验证时间段是否可预约
    if not is_time_slot_available(week_day, start_time, end_time, interval_mapping):
        messagebox.showerror("错误", "您选择的时间段不可预约，请选择其他时间。")
        return

    # 获取 place_id
    place_id = place_mapping.get(place_title)
    if place_id is None:
        messagebox.showerror("错误", f"无效的场地名称: {place_title}")
        return

    # 获取 interval_id
    interval_id = get_interval_id(week_day, start_time, end_time, interval_mapping)
    if interval_id is None:
        messagebox.showerror("错误", "无法找到匹配的时间段，请检查输入的时间和日期。")
        return

    # 生成请求数据
    data = {
        "form": {
            "uid": uid,
            "place_id": place_id,
            "place_title": place_title,
            "interval_id": interval_id,
            "start_time": start_time,
            "end_time": end_time,
            "order_date": order_date,
            "order_phone": order_phone,
            "order_name": order_name,
            "order_student_id": "",
            "gym_id": gym_data["gym_id"],
            "gym_title": gym_data["gym_title"],
            "category_id": gym_data["category_id"],
            "category_title": gym_data["category_title"],
            "teacher_status": 0,
            "is_audit": 0,
            "store_id": gym_data["store_id"],
            "order_state": "用户预约成功",
            "is_admin": ""
        }
    }

    # 启动一个新线程来处理网络请求，避免 GUI 卡死
    threading.Thread(target=send_request, args=(data,)).start()

# 发送 POST 请求的函数
def send_request(data):
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            messagebox.showinfo("成功", "预约成功！")
        else:
            messagebox.showerror("错误", f"请求失败，状态码：{response.status_code}")
    except Exception as e:
        messagebox.showerror("错误", f"请求失败：{str(e)}")

# 生成随机中文姓名
def generate_random_chinese_name():
    return fake.name()

# 生成随机手机号
def generate_random_phone():
    return fake.phone_number()

# 计算结束时间
def calculate_end_time(start_time):
    start_time_obj = datetime.strptime(start_time, "%H:%M")
    end_time_obj = start_time_obj + timedelta(hours=1)
    return end_time_obj.strftime("%H:%M")

# 根据预约日期获取周几
def get_week_day(order_date):
    date_obj = datetime.strptime(order_date, "%Y-%m-%d")
    return (date_obj.weekday() + 1) % 7

# 检查时间段是否可预约
def is_time_slot_available(week_day, start_time, end_time, interval_mapping):
    for interval in interval_mapping:
        if (interval["Week Day"] == week_day and
            interval["Start Time"] == start_time and
            interval["End Time"] == end_time):
            if interval.get("is_reserve", 1) == 0:
                return True
            else:
                return False
    # 如果没有找到匹配的时间段，则不可预约
    return False

# 根据周几、开始时间和结束时间获取 interval_id
def get_interval_id(week_day, start_time, end_time, interval_mapping):
    for interval in interval_mapping:
        if (interval["Week Day"] == week_day and
            interval["Start Time"] == start_time and
            interval["End Time"] == end_time):
            return interval["Interval ID"]
    return None

# 获取从当前日期加4天到加7天的日期列表
def get_available_dates():
    current_date = datetime.now()
    dates = [(current_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(4, 8)]
    return dates

# 显示加载窗口
def show_loading_window():
    loading_window = tk.Toplevel(root)
    loading_window.title("加载中")
    tk.Label(loading_window, text="请稍等，正在加载数据...").pack(pady=20, padx=20)
    return loading_window

# 筛选对话框
def show_filter_dialog(tree, col, event):
    unique_values = set(tree.set(child, col) for child in tree.get_children(''))
    filter_window = Toplevel(root)
    filter_window.title(f"筛选: {col}")

    # 设置对话框显示位置靠近列头
    x_offset = event.x_root
    y_offset = event.y_root
    filter_window.geometry(f"+{x_offset}+{y_offset}")

    # 创建变量存储筛选选项状态
    check_vars = {}
    for value in unique_values:
        var = IntVar(value=1)  # 默认全选
        check_vars[value] = var
        Checkbutton(filter_window, text=value, variable=var).pack(anchor='w')

    def apply_filter():
        selected_values = {val for val, var in check_vars.items() if var.get() == 1}
        for row in tree.get_children():
            if tree.set(row, col) not in selected_values:
                tree.detach(row)
            else:
                tree.reattach(row, '', 'end')
        filter_window.destroy()

    tk.Button(filter_window, text="应用", command=apply_filter).pack()

# 初始化全局排序列列表
sort_columns = []

# 转换值为合适的数据类型
def convert_value(value, col):
    # 去除空格
    value = value.strip()
    if col in ['start_time', 'end_time']:
        try:
            return datetime.strptime(value, "%H:%M")
        except ValueError:
            return datetime.min
    elif col == 'create_time':
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.min
    elif col == 'uid':
        try:
            return int(value)
        except ValueError:
            return 0
    elif col == 'order_phone':
        return value
    else:
        return value

# 多列排序函数
def sort_by(tree):
    data = list(tree.get_children(''))
    # 从次要关键字到主要关键字排序
    for col, ascending in reversed(sort_columns):
        data.sort(key=lambda x: convert_value(tree.set(x, col), col), reverse=not ascending)
    # 重新排列项
    for index, item in enumerate(data):
        tree.move(item, '', index)

# 更新列头显示排序方向
def update_column_headings():
    for col in tree["columns"]:
        # 查找该列是否在排序列表中
        for i, (sort_col, ascending) in enumerate(sort_columns):
            if sort_col == col:
                indicator = "▲" if ascending else "▼"
                tree.heading(col, text=f"{col} {indicator}")
                break
        else:
            tree.heading(col, text=col)

# 处理列头点击事件，区分左右键
def on_column_click(event):
    region = tree.identify_region(event.x, event.y)
    if region == "heading":
        column = tree.identify_column(event.x)
        col_id = tree["columns"][int(column[1:]) - 1]
        
        if event.num == 1:  # 左键单击，排序
            # 更新排序列列表
            for i, (col, ascending) in enumerate(sort_columns):
                if col == col_id:
                    ascending = not ascending  # 切换排序顺序
                    sort_columns[i] = (col_id, ascending)
                    break
            else:
                sort_columns.append((col_id, True))  # 添加到列表末尾，表示次要关键字
            sort_by(tree)
            update_column_headings()
        elif event.num == 3:  # 右键单击，筛选
            show_filter_dialog(tree, col_id, event)

# 获取已预约信息并展示
def fetch_and_show_appointments():
    selected_date = order_date_combobox.get()  # 获取用户选择的预约日期
    gym_selection = gym_combobox.get()  # 获取用户选择的场馆

    # 获取场馆数据
    gym_data = gym_options.get(gym_selection)
    if not gym_data:
        messagebox.showerror("错误", "请选择有效的场馆！")
        return

    gym_id = gym_data["gym_id"]

    url = f"https://cgyy.xiaorankeji.com/index.php?s=/api/order/listForGymOrder&state=用户预约成功,待管理员审核&orderDate={selected_date}&gymId={gym_id}"
    
    # 自定义字段
    global fields_to_extract, original_data
    fields_to_extract = ['order_name', 'place_title', 'start_time', 'end_time', 'order_phone', 'uid', 'create_time']

    # 显示加载窗口
    loading_window = show_loading_window()

    def fetch_data():
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and 'orderList' in data['data']:
                orders = data['data']['orderList']
                loading_window.destroy()

                result_window = tk.Toplevel(root)
                result_window.title(f"{selected_date}的预约信息")
                result_window.geometry("1920x1080")

                # Treeview 表格
                global tree
                tree = ttk.Treeview(result_window, columns=fields_to_extract, show='headings')

                # 设置表格标题，绑定列头点击事件
                for field in fields_to_extract:
                    tree.heading(field, text=field)

                # 设置列内容居中
                for field in fields_to_extract:
                    tree.column(field, anchor="center", width=120)

                # 绑定鼠标点击事件处理排序与筛选
                tree.bind("<Button-1>", on_column_click)
                tree.bind("<Button-3>", on_column_click)

                # 设置标签居中显示
                tree.tag_configure('center', anchor='center')

                global original_data
                original_data = orders

                # **按照指定方式排序数据**
                def sort_key(order):
                    place_title = order.get('place_title', '')
                    start_time_str = order.get('start_time', '')
                    try:
                        start_time = datetime.strptime(start_time_str, "%H:%M")
                    except ValueError:
                        start_time = datetime.min  # 处理无效的时间
                    return (place_title, start_time)

                orders.sort(key=sort_key)

                # 插入数据到表格，并应用居中对齐的标签
                for order in orders:
                    row = [order.get(field, "无数据") for field in fields_to_extract]
                    tree.insert('', 'end', values=row, tags=('center',))  # 应用居中标签

                tree.pack(expand=True, fill=tk.BOTH)

            else:
                loading_window.destroy()
                messagebox.showinfo("无数据", "该日期没有已预约信息。")

        except Exception as e:
            loading_window.destroy()
            messagebox.showerror("请求错误", f"请求失败: {e}")

    threading.Thread(target=fetch_data).start()

# 创建 Tkinter 界面
root = tk.Tk()
root.title("中国药科大学羽毛球场地预约系统")

# 设置窗口大小
root.geometry("500x500")

# 显示加载场馆数据的窗口
loading_window = show_loading_window()

def init_app():
    # 从 API 获取 gym_options 数据
    fetch_gym_data([10001, 10029])

    # 关闭加载窗口
    loading_window.destroy()

    # 创建输入标签和输入框
    tk.Label(root, text="请输入预约信息", font=("Arial", 16)).grid(row=0, column=1)

    tk.Label(root, text="学工号(必填)", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=10)
    tk.Label(root, text="场地号(例如:4)", font=("Arial", 12)).grid(row=2, column=0, padx=10, pady=10)
    tk.Label(root, text="开始时间(例如:19:00)", font=("Arial", 12)).grid(row=3, column=0, padx=10, pady=10)
    tk.Label(root, text="预约日期", font=("Arial", 12)).grid(row=4, column=0, padx=10, pady=10)
    tk.Label(root, text="姓名(留空随机生成)", font=("Arial", 12)).grid(row=5, column=0, padx=10, pady=10)
    tk.Label(root, text="联系电话(留空随机生成)", font=("Arial", 12)).grid(row=6, column=0, padx=10, pady=10)
    tk.Label(root, text="场馆选择", font=("Arial", 12)).grid(row=7, column=0, padx=10, pady=10)

    # 输入框
    global uid_entry, place_title_entry, start_time_entry, order_name_entry, order_phone_entry
    uid_entry = tk.Entry(root, font=("Arial", 12), width=25)
    place_title_entry = tk.Entry(root, font=("Arial", 12), width=25)
    start_time_entry = tk.Entry(root, font=("Arial", 12), width=25)
    order_name_entry = tk.Entry(root, font=("Arial", 12), width=25)  # 姓名输入框
    order_phone_entry = tk.Entry(root, font=("Arial", 12), width=25)  # 电话输入框

    uid_entry.grid(row=1, column=1)
    place_title_entry.grid(row=2, column=1)
    start_time_entry.grid(row=3, column=1)
    order_name_entry.grid(row=5, column=1)
    order_phone_entry.grid(row=6, column=1)

    # 预约日期下拉框
    available_dates = get_available_dates()  # 获取当前日期加4天到加7天的日期范围
    global order_date_combobox
    order_date_combobox = ttk.Combobox(root, values=available_dates, font=("Arial", 12), width=22)
    order_date_combobox.grid(row=4, column=1)
    order_date_combobox.current(0)  # 设置默认值为第一个可选日期

    # 场馆选择下拉框
    global gym_combobox
    gym_combobox = ttk.Combobox(root, values=list(gym_options.keys()), font=("Arial", 12), width=22)
    gym_combobox.grid(row=7, column=1)
    gym_combobox.current(0)  # 设置默认值

    # 创建提交按钮
    submit_button = tk.Button(root, text="提交预约", font=("Arial", 12), command=submit_form)
    submit_button.grid(row=8, column=1, pady=10)

    # 创建查看已预约按钮
    view_button = tk.Button(root, text="查看已预约", font=("Arial", 12), command=fetch_and_show_appointments)
    view_button.grid(row=9, column=1, pady=10)

# 在新线程中初始化应用程序
threading.Thread(target=init_app).start()

# 运行主循环
root.mainloop()
