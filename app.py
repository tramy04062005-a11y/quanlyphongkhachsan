```python
import streamlit as st
import sqlite3
from datetime import datetime, date
import pandas as pd
import plotly.express as px


# =========================================================
# CẤU HÌNH STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Hotel Manager",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "hotel.db"


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def init_database():

    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------
    # Bảng phòng
    # -----------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            floor INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Trống'
        )
    """)

    # -----------------------------
    # Bảng booking
    # -----------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            room_id INTEGER NOT NULL,

            guest_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            id_number TEXT,

            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,

            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,

            price_per_night REAL NOT NULL,
            total_amount REAL DEFAULT 0,

            status TEXT DEFAULT 'Đã đặt',

            note TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(room_id)
            REFERENCES rooms(id)
        )
    """)

    # -----------------------------
    # Bảng cài đặt
    # -----------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # -----------------------------
    # Dữ liệu phòng mẫu
    # -----------------------------

    cursor.execute(
        "SELECT COUNT(*) FROM rooms"
    )

    room_count = cursor.fetchone()[0]

    if room_count == 0:

        sample_rooms = [
            ("101", "Standard", 1, 800000, "Trống"),
            ("102", "Standard", 1, 800000, "Trống"),
            ("103", "Standard", 1, 800000, "Trống"),

            ("201", "Deluxe", 2, 1200000, "Trống"),
            ("202", "Deluxe", 2, 1200000, "Trống"),
            ("203", "Deluxe", 2, 1200000, "Trống"),

            ("301", "Suite", 3, 2000000, "Trống"),
            ("302", "Suite", 3, 2000000, "Trống"),

            ("401", "Villa", 4, 3500000, "Trống"),
            ("402", "Villa", 4, 3500000, "Trống")
        ]

        cursor.executemany("""
            INSERT INTO rooms
            (
                room_number,
                room_type,
                floor,
                price,
                status
            )
            VALUES (?, ?, ?, ?, ?)
        """, sample_rooms)

    # -----------------------------
    # Settings mặc định
    # -----------------------------

    default_settings = {
        "hotel_name": "My Hotel",
        "hotel_address": "Việt Nam",
        "hotel_phone": "0123 456 789"
    }

    for key, value in default_settings.items():

        cursor.execute("""
            INSERT OR IGNORE INTO settings
            (key, value)
            VALUES (?, ?)
        """, (key, value))

    conn.commit()
    conn.close()


init_database()


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def query_df(query, params=()):

    conn = get_connection()

    try:
        df = pd.read_sql_query(
            query,
            conn,
            params=params
        )
    finally:
        conn.close()

    return df


def execute_query(query, params=()):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            query,
            params
        )

        conn.commit()

        return cursor.lastrowid

    finally:
        conn.close()


def execute_transaction(queries):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        for query, params in queries:

            cursor.execute(
                query,
                params
            )

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def calculate_nights(check_in, check_out):

    nights = (
        check_out - check_in
    ).days

    return max(nights, 0)


def calculate_total(check_in, check_out, price):

    nights = calculate_nights(
        check_in,
        check_out
    )

    return nights * float(price)


def format_currency(value):

    if pd.isna(value):
        value = 0

    return f"{float(value):,.0f} ₫"


def get_setting(key, default=""):

    df = query_df(
        """
        SELECT value
        FROM settings
        WHERE key = ?
        """,
        (key,)
    )

    if df.empty:
        return default

    return df.iloc[0]["value"]


def save_setting(key, value):

    execute_query(
        """
        INSERT INTO settings
        (key, value)
        VALUES (?, ?)

        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
        """,
        (key, value)
    )


# =========================================================
# SIDEBAR
# =========================================================

hotel_name = get_setting(
    "hotel_name",
    "My Hotel"
)

st.sidebar.title(
    f"🏨 {hotel_name.upper()}"
)

st.sidebar.caption(
    "Hệ thống quản lý khách sạn"
)

menu = st.sidebar.radio(
    "MENU",
    [
        "📊 Tổng quan",
        "🛏️ Quản lý phòng",
        "📋 Đặt phòng",
        "👤 Khách đang ở",
        "💰 Doanh thu",
        "⚙️ Cài đặt"
    ]
)

st.sidebar.divider()

st.sidebar.info(
    "💾 Dữ liệu được lưu trong file hotel.db"
)


# =========================================================
# TỔNG QUAN
# =========================================================

if menu == "📊 Tổng quan":

    st.title(
        f"📊 Tổng quan - {hotel_name}"
    )

    st.caption(
        "Cập nhật: "
        + datetime.now().strftime(
            "%d/%m/%Y %H:%M"
        )
    )

    rooms = query_df("""
        SELECT *
        FROM rooms
        ORDER BY floor, room_number
    """)

    total_rooms = len(rooms)

    available = len(
        rooms[
            rooms["status"] == "Trống"
        ]
    )

    booked = len(
        rooms[
            rooms["status"] == "Đã đặt"
        ]
    )

    occupied = len(
        rooms[
            rooms["status"] == "Đang ở"
        ]
    )

    cleaning = len(
        rooms[
            rooms["status"] == "Đang dọn"
        ]
    )

    maintenance = len(
        rooms[
            rooms["status"] == "Bảo trì"
        ]
    )

    # -----------------------------
    # KPI
    # -----------------------------

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric(
        "🏨 Tổng phòng",
        total_rooms
    )

    col2.metric(
        "🟢 Trống",
        available
    )

    col3.metric(
        "🟡 Đã đặt",
        booked
    )

    col4.metric(
        "🔴 Đang ở",
        occupied
    )

    col5.metric(
        "🧹 Đang dọn",
        cleaning
    )

    col6.metric(
        "🔧 Bảo trì",
        maintenance
    )

    st.divider()

    # -----------------------------
    # BIỂU ĐỒ
    # -----------------------------

    left, right = st.columns(2)

    with left:

        st.subheader(
            "📊 Tình trạng phòng"
        )

        status_df = pd.DataFrame({
            "Trạng thái": [
                "Trống",
                "Đã đặt",
                "Đang ở",
                "Đang dọn",
                "Bảo trì"
            ],
            "Số phòng": [
                available,
                booked,
                occupied,
                cleaning,
                maintenance
            ]
        })

        if status_df["Số phòng"].sum() > 0:

            fig = px.pie(
                status_df,
                names="Trạng thái",
                values="Số phòng",
                hole=0.45
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    with right:

        st.subheader(
            "🛏️ Loại phòng"
        )

        if not rooms.empty:

            type_df = (
                rooms
                .groupby("room_type")
                .size()
                .reset_index(
                    name="Số phòng"
                )
            )

            fig2 = px.bar(
                type_df,
                x="room_type",
                y="Số phòng",
                text="Số phòng"
            )

            fig2.update_traces(
                textposition="outside"
            )

            st.plotly_chart(
                fig2,
                use_container_width=True
            )

    st.divider()

    # -----------------------------
    # KHÁCH ĐANG Ở
    # -----------------------------

    st.subheader(
        "📅 Khách đang lưu trú"
    )

    current_guests = query_df("""
        SELECT
            b.id,
            r.room_number AS "Phòng",
            b.guest_name AS "Khách hàng",
            b.phone AS "Số điện thoại",
            b.check_in AS "Check-in",
            b.check_out AS "Check-out",
            b.adults AS "Người lớn",
            b.children AS "Trẻ em",
            b.total_amount AS "Tổng tiền"
        FROM bookings b
        JOIN rooms r
            ON b.room_id = r.id
        WHERE b.status = 'Đang ở'
        ORDER BY b.check_out
    """)

    if current_guests.empty:

        st.info(
            "Hiện không có khách đang lưu trú."
        )

    else:

        st.dataframe(
            current_guests,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tổng tiền":
                    st.column_config.NumberColumn(
                        format="%d ₫"
                    )
            }
        )


# =========================================================
# QUẢN LÝ PHÒNG
# =========================================================

elif menu == "🛏️ Quản lý phòng":

    st.title(
        "🛏️ Quản lý phòng"
    )

    rooms = query_df("""
        SELECT *
        FROM rooms
        ORDER BY floor, room_number
    """)

    if rooms.empty:

        st.warning(
            "Chưa có phòng nào trong hệ thống."
        )

    else:

        col1, col2, col3 = st.columns(3)

        with col1:

            search = st.text_input(
                "🔎 Tìm phòng",
                placeholder="Nhập số phòng..."
            )

        with col2:

            status_filter = st.selectbox(
                "Trạng thái",
                [
                    "Tất cả",
                    "Trống",
                    "Đã đặt",
                    "Đang ở",
                    "Đang dọn",
                    "Bảo trì"
                ]
            )

        with col3:

            type_filter = st.selectbox(
                "Loại phòng",
                [
                    "Tất cả"
                ]
                + sorted(
                    rooms[
                        "room_type"
                    ]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

        filtered = rooms.copy()

        if search:

            filtered = filtered[
                filtered[
                    "room_number"
                ]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

        if status_filter != "Tất cả":

            filtered = filtered[
                filtered["status"]
                == status_filter
            ]

        if type_filter != "Tất cả":

            filtered = filtered[
                filtered["room_type"]
                == type_filter
            ]

        display_rooms = filtered[
            [
                "room_number",
                "room_type",
                "floor",
                "price",
                "status"
            ]
        ].rename(
            columns={
                "room_number": "Số phòng",
                "room_type": "Loại phòng",
                "floor": "Tầng",
                "price": "Giá/đêm",
                "status": "Trạng thái"
            }
        )

        st.dataframe(
            display_rooms,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Giá/đêm":
                    st.column_config.NumberColumn(
                        format="%d ₫"
                    )
            }
        )

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "➕ Thêm phòng",
            "✏️ Cập nhật phòng",
            "🧹 Hoàn tất dọn phòng",
            "🗑️ Xóa phòng"
        ]
    )

    # =====================================================
    # THÊM PHÒNG
    # =====================================================

    with tab1:

        st.subheader(
            "➕ Thêm phòng mới"
        )

        with st.form("add_room"):

            c1, c2 = st.columns(2)

            room_number = c1.text_input(
                "Số phòng *",
                placeholder="Ví dụ: 501"
            )

            room_type = c2.selectbox(
                "Loại phòng",
                [
                    "Standard",
                    "Superior",
                    "Deluxe",
                    "Suite",
                    "Villa",
                    "Family"
                ]
            )

            c3, c4 = st.columns(2)

            floor = c3.number_input(
                "Tầng",
                min_value=1,
                max_value=100,
                value=1,
                step=1
            )

            price = c4.number_input(
                "Giá phòng/đêm",
                min_value=0,
                value=800000,
                step=100000
            )

            submit = st.form_submit_button(
                "➕ Thêm phòng",
                use_container_width=True
            )

            if submit:

                room_number_clean = (
                    room_number
                    .strip()
                )

                if not room_number_clean:

                    st.error(
                        "Vui lòng nhập số phòng."
                    )

                else:

                    try:

                        execute_query(
                            """
                            INSERT INTO rooms
                            (
                                room_number,
                                room_type,
                                floor,
                                price,
                                status
                            )
                            VALUES (?, ?, ?, ?, 'Trống')
                            """,
                            (
                                room_number_clean,
                                room_type,
                                floor,
                                price
                            )
                        )

                        st.success(
                            f"Đã thêm phòng "
                            f"{room_number_clean}."
                        )

                        st.rerun()

                    except sqlite3.IntegrityError:

                        st.error(
                            "Số phòng này đã tồn tại."
                        )

    # =====================================================
    # SỬA PHÒNG
    # =====================================================

    with tab2:

        st.subheader(
            "✏️ Cập nhật thông tin phòng"
        )

        rooms_edit = query_df("""
            SELECT *
            FROM rooms
            ORDER BY floor, room_number
        """)

        if rooms_edit.empty:

            st.info(
                "Chưa có phòng."
            )

        else:

            room_options = {
                (
                    f"Phòng {row['room_number']} - "
                    f"{row['room_type']}"
                ):
                row["id"]

                for _, row
                in rooms_edit.iterrows()
            }

            selected_room = st.selectbox(
                "Chọn phòng",
                list(
                    room_options.keys()
                ),
                key="edit_room_select"
            )

            room_id = room_options[
                selected_room
            ]

            room = rooms_edit[
                rooms_edit["id"]
                == room_id
            ].iloc[0]

            room_types = [
                "Standard",
                "Superior",
                "Deluxe",
                "Suite",
                "Villa",
                "Family"
            ]

            current_type = room["room_type"]

            if current_type not in room_types:
                room_types.append(
                    current_type
                )

            status_list = [
                "Trống",
                "Đã đặt",
                "Đang ở",
                "Đang dọn",
                "Bảo trì"
            ]

            with st.form(
                "edit_room_form"
            ):

                c1, c2 = st.columns(2)

                new_type = c1.selectbox(
                    "Loại phòng",
                    room_types,
                    index=room_types.index(
                        current_type
                    )
                )

                new_floor = c2.number_input(
                    "Tầng",
                    min_value=1,
                    max_value=100,
                    value=int(
                        room["floor"]
                    )
                )

                c3, c4 = st.columns(2)

                new_price = c3.number_input(
                    "Giá phòng",
                    min_value=0,
                    value=int(
                        room["price"]
                    ),
                    step=100000
                )

                new_status = c4.selectbox(
                    "Trạng thái",
                    status_list,
                    index=status_list.index(
                        room["status"]
                    )
                )

                save = st.form_submit_button(
                    "💾 Lưu thay đổi",
                    use_container_width=True
                )

                if save:

                    execute_query(
                        """
                        UPDATE rooms
                        SET
                            room_type = ?,
                            floor = ?,
                            price = ?,
                            status = ?
                        WHERE id = ?
                        """,
                        (
                            new_type,
                            new_floor,
                            new_price,
                            new_status,
                            room_id
                        )
                    )

                    st.success(
                        "Đã cập nhật phòng."
                    )

                    st.rerun()

    # =====================================================
    # HOÀN TẤT DỌN PHÒNG
    # =====================================================

    with tab3:

        st.subheader(
            "🧹 Hoàn tất dọn phòng"
        )

        cleaning_rooms = query_df("""
            SELECT *
            FROM rooms
            WHERE status = 'Đang dọn'
            ORDER BY room_number
        """)

        if cleaning_rooms.empty:

            st.success(
                "Không có phòng đang chờ dọn."
            )

        else:

            cleaning_options = {
                (
                    f"Phòng {row['room_number']} - "
                    f"{row['room_type']}"
                ):
                row["id"]

                for _, row
                in cleaning_rooms.iterrows()
            }

            selected_cleaning = st.selectbox(
                "Chọn phòng đã dọn xong",
                list(
                    cleaning_options.keys()
                )
            )

            cleaning_id = cleaning_options[
                selected_cleaning
            ]

            if st.button(
                "✅ Đã dọn xong - Phòng trống",
                use_container_width=True
            ):

                execute_query(
                    """
                    UPDATE rooms
                    SET status = 'Trống'
                    WHERE id = ?
                    """,
                    (cleaning_id,)
                )

                st.success(
                    "Phòng đã chuyển sang trạng thái Trống."
                )

                st.rerun()

    # =====================================================
    # XÓA PHÒNG
    # =====================================================

    with tab4:

        st.subheader(
            "🗑️ Xóa phòng"
        )

        rooms_delete = query_df("""
            SELECT *
            FROM rooms
            ORDER BY floor, room_number
        """)

        if rooms_delete.empty:

            st.info(
                "Chưa có phòng."
            )

        else:

            room_options_delete = {
                f"Phòng {row['room_number']}":
                row["id"]

                for _, row
                in rooms_delete.iterrows()
            }

            delete_room_name = st.selectbox(
                "Chọn phòng cần xóa",
                list(
                    room_options_delete.keys()
                )
            )

            delete_id = room_options_delete[
                delete_room_name
            ]

            st.warning(
                "Phòng đã từng có lịch sử đặt phòng "
                "sẽ không thể xóa."
            )

            if st.button(
                "🗑️ Xóa phòng",
                type="secondary"
            ):

                booking_count = query_df(
                    """
                    SELECT COUNT(*) AS count
                    FROM bookings
                    WHERE room_id = ?
                    """,
                    (delete_id,)
                ).iloc[0]["count"]

                if booking_count > 0:

                    st.error(
                        "Không thể xóa phòng "
                        "đã có lịch sử đặt phòng."
                    )

                else:

                    execute_query(
                        """
                        DELETE FROM rooms
                        WHERE id = ?
                        """,
                        (delete_id,)
                    )

                    st.success(
                        "Đã xóa phòng."
                    )

                    st.rerun()


# =========================================================
# ĐẶT PHÒNG
# =========================================================

elif menu == "📋 Đặt phòng":

    st.title(
        "📋 Quản lý đặt phòng"
    )

    tab1, tab2 = st.tabs(
        [
            "➕ Tạo đặt phòng",
            "📑 Danh sách đặt phòng"
        ]
    )

    # =====================================================
    # TẠO BOOKING
    # =====================================================

    with tab1:

        available_rooms = query_df("""
            SELECT *
            FROM rooms
            WHERE status = 'Trống'
            ORDER BY room_number
        """)

        if available_rooms.empty:

            st.warning(
                "Hiện không có phòng trống."
            )

        else:

            with st.form(
                "new_booking"
            ):

                room_options = {
                    (
                        f"Phòng {row['room_number']} - "
                        f"{row['room_type']} - "
                        f"{format_currency(row['price'])}/đêm"
                    ):
                    row["id"]

                    for _, row
                    in available_rooms.iterrows()
                }

                room_label = st.selectbox(
                    "🛏️ Chọn phòng",
                    list(
                        room_options.keys()
                    )
                )

                room_id = room_options[
                    room_label
                ]

                selected_room = available_rooms[
                    available_rooms["id"]
                    == room_id
                ].iloc[0]

                st.info(
                    "💰 Giá phòng: "
                    + format_currency(
                        selected_room["price"]
                    )
                    + "/đêm"
                )

                c1, c2 = st.columns(2)

                guest_name = c1.text_input(
                    "👤 Họ tên khách *"
                )

                phone = c2.text_input(
                    "📞 Số điện thoại"
                )

                c3, c4 = st.columns(2)

                email = c3.text_input(
                    "📧 Email"
                )

                id_number = c4.text_input(
                    "🪪 CCCD/Passport"
                )

                c5, c6 = st.columns(2)

                check_in = c5.date_input(
                    "📅 Ngày check-in",
                    value=date.today()
                )

                check_out = c6.date_input(
                    "📅 Ngày check-out",
                    value=date.today()
                )

                c7, c8 = st.columns(2)

                adults = c7.number_input(
                    "Người lớn",
                    min_value=1,
                    value=1,
                    step=1
                )

                children = c8.number_input(
                    "Trẻ em",
                    min_value=0,
                    value=0,
                    step=1
                )

                note = st.text_area(
                    "📝 Ghi chú"
                )

                nights = calculate_nights(
                    check_in,
                    check_out
                )

                total = calculate_total(
                    check_in,
                    check_out,
                    selected_room["price"]
                )

                if nights > 0:

                    st.success(
                        f"🌙 {nights} đêm • "
                        f"💰 Tổng tiền dự kiến: "
                        f"{format_currency(total)}"
                    )

                else:

                    st.warning(
                        "Ngày check-out phải sau "
                        "ngày check-in."
                    )

                submit_booking = st.form_submit_button(
                    "✅ Xác nhận đặt phòng",
                    use_container_width=True
                )

                if submit_booking:

                    guest_name_clean = (
                        guest_name
                        .strip()
                    )

                    if not guest_name_clean:

                        st.error(
                            "Vui lòng nhập tên khách."
                        )

                    elif check_out <= check_in:

                        st.error(
                            "Ngày check-out phải sau "
                            "ngày check-in."
                        )

                    else:

                        # Kiểm tra phòng vẫn còn trống
                        room_check = query_df(
                            """
                            SELECT status
                            FROM rooms
                            WHERE id = ?
                            """,
                            (room_id,)
                        )

                        if (
                            room_check.empty
                            or room_check.iloc[0]["status"]
                            != "Trống"
                        ):

                            st.error(
                                "Phòng vừa được sử dụng "
                                "hoặc đặt bởi người khác. "
                                "Vui lòng chọn phòng khác."
                            )

                        else:

                            try:

                                execute_transaction([
                                    (
                                        """
                                        INSERT INTO bookings
                                        (
                                            room_id,
                                            guest_name,
                                            phone,
                                            email,
                                            id_number,
                                            check_in,
                                            check_out,
                                            adults,
                                            children,
                                            price_per_night,
                                            total_amount,
                                            status,
                                            note
                                        )
                                        VALUES
                                        (
                                            ?, ?, ?, ?, ?,
                                            ?, ?, ?, ?, ?,
                                            ?, ?, ?
                                        )
                                        """,
                                        (
                                            room_id,
                                            guest_name_clean,
                                            phone.strip(),
                                            email.strip(),
                                            id_number.strip(),
                                            str(check_in),
                                            str(check_out),
                                            adults,
                                            children,
                                            selected_room["price"],
                                            total,
                                            "Đã đặt",
                                            note.strip()
                                        )
                                    ),
                                    (
                                        """
                                        UPDATE rooms
                                        SET status = 'Đã đặt'
                                        WHERE id = ?
                                        """,
                                        (room_id,)
                                    )
                                ])

                                st.success(
                                    f"Đã đặt phòng "
                                    f"{selected_room['room_number']} "
                                    f"cho "
                                    f"{guest_name_clean}."
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    "Không thể tạo đặt phòng: "
                                    + str(e)
                                )

    # =====================================================
    # DANH SÁCH BOOKING
    # =====================================================

    with tab2:

        bookings = query_df("""
            SELECT
                b.id,
                r.room_number AS "Phòng",
                r.room_type AS "Loại phòng",
                b.guest_name AS "Khách hàng",
                b.phone AS "Số điện thoại",
                b.check_in AS "Check-in",
                b.check_out AS "Check-out",
                b.adults AS "Người lớn",
                b.children AS "Trẻ em",
                b.total_amount AS "Tổng tiền",
                b.status AS "Trạng thái",
                b.note AS "Ghi chú"
            FROM bookings b
            JOIN rooms r
                ON b.room_id = r.id
            ORDER BY b.check_in DESC, b.id DESC
        """)

        if bookings.empty:

            st.info(
                "Chưa có dữ liệu đặt phòng."
            )

        else:

            status_filter_booking = st.selectbox(
                "🔎 Lọc trạng thái",
                [
                    "Tất cả",
                    "Đã đặt",
                    "Đang ở",
                    "Đã trả phòng",
                    "Đã hủy"
                ]
            )

            display_bookings = bookings.copy()

            if (
                status_filter_booking
                != "Tất cả"
            ):

                display_bookings = (
                    display_bookings[
                        display_bookings[
                            "Trạng thái"
                        ]
                        == status_filter_booking
                    ]
                )

            st.dataframe(
                display_bookings,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tổng tiền":
                        st.column_config.NumberColumn(
                            format="%d ₫"
                        )
                }
            )

            st.divider()

            st.subheader(
                "⚙️ Xử lý đặt phòng"
            )

            booking_ids = (
                bookings["id"]
                .tolist()
            )

            selected_booking_id = st.selectbox(
                "Chọn mã đặt phòng",
                booking_ids,
                format_func=lambda x:
                    f"Booking #{x}"
            )

            booking = bookings[
                bookings["id"]
                == selected_booking_id
            ].iloc[0]

            st.info(
                f"Phòng {booking['Phòng']} • "
                f"{booking['Khách hàng']} • "
                f"{booking['Trạng thái']}"
            )

            c1, c2, c3 = st.columns(3)

            # -----------------------------
            # CHECK-IN
            # -----------------------------

            with c1:

                if st.button(
                    "🔑 Check-in",
                    use_container_width=True
                ):

                    if booking["Trạng thái"] != "Đã đặt":

                        st.error(
                            "Chỉ booking ở trạng thái "
                            "'Đã đặt' mới có thể check-in."
                        )

                    else:

                        room_status = query_df(
                            """
                            SELECT status
                            FROM rooms
                            WHERE room_number = ?
                            """,
                            (booking["Phòng"],)
                        )

                        if (
                            room_status.empty
                            or room_status.iloc[0]["status"]
                            != "Đã đặt"
                        ):

                            st.error(
                                "Trạng thái phòng không hợp lệ."
                            )

                        else:

                            execute_transaction([
                                (
                                    """
                                    UPDATE bookings
                                    SET status = 'Đang ở'
                                    WHERE id = ?
                                    """,
                                    (selected_booking_id,)
                                ),
                                (
                                    """
                                    UPDATE rooms
                                    SET status = 'Đang ở'
                                    WHERE room_number = ?
                                    """,
                                    (booking["Phòng"],)
                                )
                            ])

                            st.success(
                                "Check-in thành công."
                            )

                            st.rerun()

            # -----------------------------
            # CHECK-OUT
            # -----------------------------

            with c2:

                if st.button(
                    "🚪 Check-out",
                    use_container_width=True
                ):

                    if booking["Trạng thái"] != "Đang ở":

                        st.error(
                            "Chỉ khách đang ở mới "
                            "có thể check-out."
                        )

                    else:

                        execute_transaction([
                            (
                                """
                                UPDATE bookings
                                SET status = 'Đã trả phòng'
                                WHERE id = ?
                                """,
                                (selected_booking_id,)
                            ),
                            (
                                """
                                UPDATE rooms
                                SET status = 'Đang dọn'
                                WHERE room_number = ?
                                """,
                                (booking["Phòng"],)
                            )
                        ])

                        st.success(
                            "Check-out thành công. "
                            "Phòng đã chuyển sang Đang dọn."
                        )

                        st.rerun()

            # -----------------------------
            # HỦY BOOKING
            # -----------------------------

            with c3:

                if st.button(
                    "❌ Hủy đặt phòng",
                    use_container_width=True
                ):

                    if booking["Trạng thái"] != "Đã đặt":

                        st.error(
                            "Chỉ booking chưa check-in "
                            "mới có thể hủy."
                        )

                    else:

                        execute_transaction([
                            (
                                """
                                UPDATE bookings
                                SET status = 'Đã hủy'
                                WHERE id = ?
                                """,
                                (selected_booking_id,)
                            ),
                            (
                                """
                                UPDATE rooms
                                SET status = 'Trống'
                                WHERE room_number = ?
                                """,
                                (booking["Phòng"],)
                            )
                        ])

                        st.warning(
                            "Đã hủy đặt phòng."
                        )

                        st.rerun()


# =========================================================
# KHÁCH ĐANG Ở
# =========================================================

elif menu == "👤 Khách đang ở":

    st.title(
        "👤 Khách đang lưu trú"
    )

    guests = query_df("""
        SELECT
            b.id,
            r.room_number AS "Phòng",
            r.room_type AS "Loại phòng",
            b.guest_name AS "Khách hàng",
            b.phone AS "Số điện thoại",
            b.email AS "Email",
            b.id_number AS "CCCD/Passport",
            b.check_in AS "Check-in",
            b.check_out AS "Check-out",
            b.adults AS "Người lớn",
            b.children AS "Trẻ em",
            b.total_amount AS "Tổng tiền",
            b.note AS "Ghi chú"
        FROM bookings b
        JOIN rooms r
            ON b.room_id = r.id
        WHERE b.status = 'Đang ở'
        ORDER BY b.check_out
    """)

    if guests.empty:

        st.info(
            "Hiện không có khách đang lưu trú."
        )

    else:

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "👤 Booking đang ở",
            len(guests)
        )

        col2.metric(
            "🛏️ Phòng đang sử dụng",
            guests["Phòng"].nunique()
        )

        total_guest = (
            guests["Người lớn"].sum()
            + guests["Trẻ em"].sum()
        )

        col3.metric(
            "👨‍👩‍👧 Tổng số người",
            int(total_guest)
        )

        st.divider()

        st.dataframe(
            guests,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tổng tiền":
                    st.column_config.NumberColumn(
                        format="%d ₫"
                    )
            }
        )


# =========================================================
# DOANH THU
# =========================================================

elif menu == "💰 Doanh thu":

    st.title(
        "💰 Doanh thu"
    )

    revenue = query_df("""
        SELECT
            b.id,
            r.room_number AS "Phòng",
            r.room_type AS "Loại phòng",
            b.guest_name AS "Khách hàng",
            b.check_in AS "Check-in",
            b.check_out AS "Check-out",
            b.total_amount AS "Doanh thu",
            b.status AS "Trạng thái"
        FROM bookings b
        JOIN rooms r
            ON b.room_id = r.id
        WHERE b.status != 'Đã hủy'
        ORDER BY b.check_in DESC
    """)

    if revenue.empty:

        st.info(
            "Chưa có dữ liệu doanh thu."
        )

    else:

        total_revenue = (
            revenue["Doanh thu"]
            .sum()
        )

        completed_revenue = (
            revenue[
                revenue["Trạng thái"]
                == "Đã trả phòng"
            ]["Doanh thu"]
            .sum()
        )

        staying_revenue = (
            revenue[
                revenue["Trạng thái"]
                == "Đang ở"
            ]["Doanh thu"]
            .sum()
        )

        booked_revenue = (
            revenue[
                revenue["Trạng thái"]
                == "Đã đặt"
            ]["Doanh thu"]
            .sum()
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "💰 Tổng",
            format_currency(
                total_revenue
            )
        )

        col2.metric(
            "🚪 Đã trả phòng",
            format_currency(
                completed_revenue
            )
        )

        col3.metric(
            "🏨 Đang ở",
            format_currency(
                staying_revenue
            )
        )

        col4.metric(
            "📅 Đã đặt",
            format_currency(
                booked_revenue
            )
        )

        st.divider()

        # -----------------------------
        # DOANH THU THEO LOẠI PHÒNG
        # -----------------------------

        st.subheader(
            "📊 Doanh thu theo loại phòng"
        )

        revenue_by_type = query_df("""
            SELECT
                r.room_type AS "Loại phòng",
                SUM(b.total_amount) AS "Doanh thu"
            FROM bookings b
            JOIN rooms r
                ON b.room_id = r.id
            WHERE b.status != 'Đã hủy'
            GROUP BY r.room_type
            ORDER BY "Doanh thu" DESC
        """)

        if not revenue_by_type.empty:

            fig = px.bar(
                revenue_by_type,
                x="Loại phòng",
                y="Doanh thu",
                text="Doanh thu"
            )

            fig.update_traces(
                texttemplate="%{text:,.0f} ₫",
                textposition="outside"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        # -----------------------------
        # DOANH THU THEO TRẠNG THÁI
        # -----------------------------

        st.subheader(
            "📈 Doanh thu theo trạng thái"
        )

        revenue_status = (
            revenue
            .groupby("Trạng thái")[
                "Doanh thu"
            ]
            .sum()
            .reset_index()
        )

        fig_status = px.bar(
            revenue_status,
            x="Trạng thái",
            y="Doanh thu",
            text="Doanh thu"
        )

        fig_status.update_traces(
            texttemplate="%{text:,.0f} ₫",
            textposition="outside"
        )

        st.plotly_chart(
            fig_status,
            use_container_width=True
        )

        st.subheader(
            "📑 Chi tiết doanh thu"
        )

        st.dataframe(
            revenue,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Doanh thu":
                    st.column_config.NumberColumn(
                        format="%d ₫"
                    )
            }
        )


# =========================================================
# CÀI ĐẶT
# =========================================================

elif menu == "⚙️ Cài đặt":

    st.title(
        "⚙️ Cài đặt"
    )

    st.subheader(
        "🏨 Thông tin khách sạn"
    )

    current_hotel_name = get_setting(
        "hotel_name",
        "My Hotel"
    )

    current_address = get_setting(
        "hotel_address",
        "Việt Nam"
    )

    current_phone = get_setting(
        "hotel_phone",
        "0123 456 789"
    )

    with st.form(
        "hotel_settings"
    ):

        new_hotel_name = st.text_input(
            "Tên khách sạn",
            value=current_hotel_name
        )

        new_address = st.text_input(
            "Địa chỉ",
            value=current_address
        )

        new_phone = st.text_input(
            "Số điện thoại",
            value=current_phone
        )

        save_settings = st.form_submit_button(
            "💾 Lưu thông tin",
            use_container_width=True
        )

        if save_settings:

            save_setting(
                "hotel_name",
                new_hotel_name.strip()
            )

            save_setting(
                "hotel_address",
                new_address.strip()
            )

            save_setting(
                "hotel_phone",
                new_phone.strip()
            )

            st.success(
                "Đã lưu thông tin khách sạn."
            )

            st.rerun()

    st.divider()

    # =====================================================
    # DATABASE
    # =====================================================

    st.subheader(
        "🗄️ Database"
    )

    st.info(
        "Dữ liệu của hệ thống được lưu "
        "trong file hotel.db."
    )

    st.warning(
        "⚠️ Không xóa file hotel.db nếu "
        "bạn muốn giữ dữ liệu."
    )

    st.divider()

    # =====================================================
    # THỐNG KÊ
    # =====================================================

    st.subheader(
        "📌 Thống kê database"
    )

    rooms_count = query_df(
        """
        SELECT COUNT(*) AS count
        FROM rooms
        """
    ).iloc[0]["count"]

    bookings_count = query_df(
        """
        SELECT COUNT(*) AS count
        FROM bookings
        """
    ).iloc[0]["count"]

    active_bookings = query_df(
        """
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE status IN ('Đã đặt', 'Đang ở')
        """
    ).iloc[0]["count"]

    completed_bookings = query_df(
        """
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE status = 'Đã trả phòng'
        """
    ).iloc[0]["count"]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🏨 Số phòng",
        int(rooms_count)
    )

    c2.metric(
        "📋 Tổng lượt đặt",
        int(bookings_count)
    )

    c3.metric(
        "🟢 Booking đang hoạt động",
        int(active_bookings)
    )

    c4.metric(
        "🚪 Đã trả phòng",
        int(completed_bookings)
    )

    st.divider()

    st.caption(
        "Hotel Manager • Streamlit • SQLite • Plotly"
    )
