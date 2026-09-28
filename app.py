import streamlit as st
import sqlite3
from datetime import datetime, date
import pandas as pd
import plotly.express as px

# =========================================================
# CẤU HÌNH
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
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

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
            status TEXT DEFAULT 'Đang ở',
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        )
    """)

    # Tạo dữ liệu phòng mẫu nếu database chưa có phòng
    cursor.execute("SELECT COUNT(*) FROM rooms")
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
            ("402", "Villa", 4, 3500000, "Trống"),
        ]

        cursor.executemany("""
            INSERT INTO rooms
            (room_number, room_type, floor, price, status)
            VALUES (?, ?, ?, ?, ?)
        """, sample_rooms)

    conn.commit()
    conn.close()


init_database()

# =========================================================
# HÀM DATABASE
# =========================================================

def query_df(query, params=()):
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def execute_query(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def calculate_total(check_in, check_out, price):
    nights = (check_out - check_in).days

    if nights <= 0:
        nights = 1

    return nights * price


def format_currency(value):
    return f"{value:,.0f} ₫"


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🏨 HOTEL MANAGER")
st.sidebar.caption("Hệ thống quản lý khách sạn")

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
    "💾 Dữ liệu được lưu tự động trong file hotel.db"
)

# =========================================================
# TỔNG QUAN
# =========================================================

if menu == "📊 Tổng quan":

    st.title("📊 Tổng quan khách sạn")
    st.caption(f"Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    rooms = query_df("SELECT * FROM rooms")

    total_rooms = len(rooms)
    available = len(rooms[rooms["status"] == "Trống"])
    booked = len(rooms[rooms["status"] == "Đã đặt"])
    occupied = len(rooms[rooms["status"] == "Đang ở"])
    cleaning = len(rooms[rooms["status"] == "Đang dọn"])
    maintenance = len(rooms[rooms["status"] == "Bảo trì"])

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("🏨 Tổng phòng", total_rooms)
    col2.metric("🟢 Trống", available)
    col3.metric("🟡 Đã đặt", booked)
    col4.metric("🔴 Đang ở", occupied)
    col5.metric("🧹 Đang dọn", cleaning)
    col6.metric("🔧 Bảo trì", maintenance)

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Tình trạng phòng")

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

        fig = px.pie(
            status_df,
            names="Trạng thái",
            values="Số phòng",
            hole=0.45
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Loại phòng")

        type_df = rooms.groupby(
            "room_type"
        ).size().reset_index(name="Số phòng")

        fig2 = px.bar(
            type_df,
            x="room_type",
            y="Số phòng",
            text="Số phòng"
        )

        fig2.update_traces(textposition="outside")

        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.subheader("📅 Khách đang lưu trú")

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
        JOIN rooms r ON b.room_id = r.id
        WHERE b.status = 'Đang ở'
        ORDER BY b.check_out
    """)

    if current_guests.empty:
        st.info("Hiện không có khách đang lưu trú.")
    else:
        st.dataframe(
            current_guests,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# QUẢN LÝ PHÒNG
# =========================================================

elif menu == "🛏️ Quản lý phòng":

    st.title("🛏️ Quản lý phòng")

    rooms = query_df("""
        SELECT *
        FROM rooms
        ORDER BY floor, room_number
    """)

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
            ["Tất cả"] + sorted(rooms["room_type"].unique().tolist())
        )

    filtered = rooms.copy()

    if search:
        filtered = filtered[
            filtered["room_number"].astype(str).str.contains(
                search,
                case=False
            )
        ]

    if status_filter != "Tất cả":
        filtered = filtered[
            filtered["status"] == status_filter
        ]

    if type_filter != "Tất cả":
        filtered = filtered[
            filtered["room_type"] == type_filter
        ]

    st.dataframe(
        filtered[
            [
                "room_number",
                "room_type",
                "floor",
                "price",
                "status"
            ]
        ].rename(columns={
            "room_number": "Số phòng",
            "room_type": "Loại phòng",
            "floor": "Tầng",
            "price": "Giá/đêm",
            "status": "Trạng thái"
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Giá/đêm": st.column_config.NumberColumn(
                format="%d ₫"
            )
        }
    )

    st.divider()

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Thêm phòng",
            "✏️ Cập nhật phòng",
            "🗑️ Xóa phòng"
        ]
    )

    # -----------------------------------------------------
    # THÊM PHÒNG
    # -----------------------------------------------------

    with tab1:

        st.subheader("Thêm phòng mới")

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
                value=1
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

                if not room_number.strip():
                    st.error("Vui lòng nhập số phòng.")

                else:
                    try:
                        execute_query("""
                            INSERT INTO rooms
                            (room_number, room_type, floor, price, status)
                            VALUES (?, ?, ?, ?, 'Trống')
                        """, (
                            room_number.strip(),
                            room_type,
                            floor,
                            price
                        ))

                        st.success(
                            f"Đã thêm phòng {room_number}."
                        )

                        st.rerun()

                    except sqlite3.IntegrityError:
                        st.error(
                            "Số phòng này đã tồn tại."
                        )

    # -----------------------------------------------------
    # SỬA PHÒNG
    # -----------------------------------------------------

    with tab2:

        st.subheader("Cập nhật thông tin phòng")

        if rooms.empty:
            st.info("Chưa có phòng.")
        else:

            room_options = {
                f"Phòng {row['room_number']} - {row['room_type']}":
                row["id"]
                for _, row in rooms.iterrows()
            }

            selected_room = st.selectbox(
                "Chọn phòng",
                list(room_options.keys())
            )

            room_id = room_options[selected_room]

            room = rooms[
                rooms["id"] == room_id
            ].iloc[0]

            with st.form("edit_room"):

                c1, c2 = st.columns(2)

                new_type = c1.selectbox(
                    "Loại phòng",
                    [
                        "Standard",
                        "Superior",
                        "Deluxe",
                        "Suite",
                        "Villa",
                        "Family"
                    ],
                    index=[
                        "Standard",
                        "Superior",
                        "Deluxe",
                        "Suite",
                        "Villa",
                        "Family"
                    ].index(room["room_type"])
                )

                new_floor = c2.number_input(
                    "Tầng",
                    min_value=1,
                    max_value=100,
                    value=int(room["floor"])
                )

                c3, c4 = st.columns(2)

                new_price = c3.number_input(
                    "Giá phòng",
                    min_value=0,
                    value=int(room["price"]),
                    step=100000
                )

                new_status = c4.selectbox(
                    "Trạng thái",
                    [
                        "Trống",
                        "Đã đặt",
                        "Đang ở",
                        "Đang dọn",
                        "Bảo trì"
                    ],
                    index=[
                        "Trống",
                        "Đã đặt",
                        "Đang ở",
                        "Đang dọn",
                        "Bảo trì"
                    ].index(room["status"])
                )

                save = st.form_submit_button(
                    "💾 Lưu thay đổi",
                    use_container_width=True
                )

                if save:

                    execute_query("""
                        UPDATE rooms
                        SET room_type = ?,
                            floor = ?,
                            price = ?,
                            status = ?
                        WHERE id = ?
                    """, (
                        new_type,
                        new_floor,
                        new_price,
                        new_status,
                        room_id
                    ))

                    st.success("Đã cập nhật phòng.")
                    st.rerun()

    # -----------------------------------------------------
    # XÓA PHÒNG
    # -----------------------------------------------------

    with tab3:

        st.subheader("Xóa phòng")

        if rooms.empty:
            st.info("Chưa có phòng.")
        else:

            room_options_delete = {
                f"Phòng {row['room_number']}":
                row["id"]
                for _, row in rooms.iterrows()
            }

            delete_room_name = st.selectbox(
                "Chọn phòng cần xóa",
                list(room_options_delete.keys())
            )

            delete_id = room_options_delete[
                delete_room_name
            ]

            if st.button(
                "🗑️ Xóa phòng",
                type="secondary"
            ):

                booking_count = query_df("""
                    SELECT *
                    FROM bookings
                    WHERE room_id = ?
                """, (delete_id,))

                if not booking_count.empty:
                    st.error(
                        "Không thể xóa phòng đã có lịch sử đặt phòng."
                    )
                else:

                    execute_query(
                        "DELETE FROM rooms WHERE id = ?",
                        (delete_id,)
                    )

                    st.success("Đã xóa phòng.")
                    st.rerun()


# =========================================================
# ĐẶT PHÒNG
# =========================================================

elif menu == "📋 Đặt phòng":

    st.title("📋 Quản lý đặt phòng")

    tab1, tab2 = st.tabs(
        [
            "➕ Tạo đặt phòng",
            "📑 Danh sách đặt phòng"
        ]
    )

    # -----------------------------------------------------
    # TẠO BOOKING
    # -----------------------------------------------------

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

            with st.form("new_booking"):

                room_options = {
                    f"Phòng {row['room_number']} - "
                    f"{row['room_type']} - "
                    f"{format_currency(row['price'])}/đêm":
                    row["id"]
                    for _, row in available_rooms.iterrows()
                }

                room_label = st.selectbox(
                    "🛏️ Chọn phòng",
                    list(room_options.keys())
                )

                room_id = room_options[room_label]

                selected_room = available_rooms[
                    available_rooms["id"] == room_id
                ].iloc[0]

                st.info(
                    f"Giá phòng: "
                    f"{format_currency(selected_room['price'])}/đêm"
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
                    value=1
                )

                children = c8.number_input(
                    "Trẻ em",
                    min_value=0,
                    value=0
                )

                note = st.text_area(
                    "📝 Ghi chú"
                )

                total = calculate_total(
                    check_in,
                    check_out,
                    selected_room["price"]
                )

                st.success(
                    f"💰 Tổng tiền dự kiến: "
                    f"{format_currency(total)}"
                )

                submit_booking = st.form_submit_button(
                    "✅ Xác nhận đặt phòng",
                    use_container_width=True
                )

                if submit_booking:

                    if not guest_name.strip():
                        st.error(
                            "Vui lòng nhập tên khách."
                        )

                    elif check_out <= check_in:
                        st.error(
                            "Ngày check-out phải sau ngày check-in."
                        )

                    else:

                        execute_query("""
                            INSERT INTO bookings (
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
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            room_id,
                            guest_name.strip(),
                            phone,
                            email,
                            id_number,
                            str(check_in),
                            str(check_out),
                            adults,
                            children,
                            selected_room["price"],
                            total,
                            "Đã đặt",
                            note
                        ))

                        execute_query("""
                            UPDATE rooms
                            SET status = 'Đã đặt'
                            WHERE id = ?
                        """, (room_id,))

                        st.success(
                            f"Đã đặt phòng "
                            f"{selected_room['room_number']} "
                            f"cho {guest_name}."
                        )

                        st.rerun()

    # -----------------------------------------------------
    # DANH SÁCH BOOKING
    # -----------------------------------------------------

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
            JOIN rooms r ON b.room_id = r.id
            ORDER BY b.check_in DESC
        """)

        if bookings.empty:
            st.info("Chưa có dữ liệu đặt phòng.")

        else:

            status_filter_booking = st.selectbox(
                "Lọc trạng thái",
                [
                    "Tất cả",
                    "Đã đặt",
                    "Đang ở",
                    "Đã trả phòng",
                    "Đã hủy"
                ]
            )

            display_bookings = bookings.copy()

            if status_filter_booking != "Tất cả":
                display_bookings = display_bookings[
                    display_bookings["Trạng thái"]
                    == status_filter_booking
                ]

            st.dataframe(
                display_bookings,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tổng tiền": st.column_config.NumberColumn(
                        format="%d ₫"
                    )
                }
            )

            st.divider()

            st.subheader("⚙️ Xử lý đặt phòng")

            booking_ids = bookings["id"].tolist()

            selected_booking_id = st.selectbox(
                "Chọn mã đặt phòng",
                booking_ids
            )

            booking = bookings[
                bookings["id"] == selected_booking_id
            ].iloc[0]

            c1, c2, c3 = st.columns(3)

            with c1:

                if st.button(
                    "🔑 Check-in",
                    use_container_width=True
                ):

                    execute_query("""
                        UPDATE bookings
                        SET status = 'Đang ở'
                        WHERE id = ?
                    """, (selected_booking_id,))

                    execute_query("""
                        UPDATE rooms
                        SET status = 'Đang ở'
                        WHERE room_number = ?
                    """, (booking["Phòng"],))

                    st.success("Check-in thành công.")
                    st.rerun()

            with c2:

                if st.button(
                    "🚪 Check-out",
                    use_container_width=True
                ):

                    execute_query("""
                        UPDATE bookings
                        SET status = 'Đã trả phòng'
                        WHERE id = ?
                    """, (selected_booking_id,))

                    execute_query("""
                        UPDATE rooms
                        SET status = 'Đang dọn'
                        WHERE room_number = ?
                    """, (booking["Phòng"],))

                    st.success(
                        "Check-out thành công. "
                        "Phòng chuyển sang trạng thái đang dọn."
                    )

                    st.rerun()

            with c3:

                if st.button(
                    "❌ Hủy đặt phòng",
                    use_container_width=True
                ):

                    execute_query("""
                        UPDATE bookings
                        SET status = 'Đã hủy'
                        WHERE id = ?
                    """, (selected_booking_id,))

                    execute_query("""
                        UPDATE rooms
                        SET status = 'Trống'
                        WHERE room_number = ?
                    """, (booking["Phòng"],))

                    st.warning("Đã hủy đặt phòng.")
                    st.rerun()


# =========================================================
# KHÁCH ĐANG Ở
# =========================================================

elif menu == "👤 Khách đang ở":

    st.title("👤 Khách đang lưu trú")

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
        JOIN rooms r ON b.room_id = r.id
        WHERE b.status = 'Đang ở'
        ORDER BY b.check_out
    """)

    if guests.empty:
        st.info("Hiện không có khách đang lưu trú.")

    else:

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "👤 Khách đang ở",
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
            total_guest
        )

        st.divider()

        st.dataframe(
            guests,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tổng tiền": st.column_config.NumberColumn(
                    format="%d ₫"
                )
            }
        )


# =========================================================
# DOANH THU
# =========================================================

elif menu == "💰 Doanh thu":

    st.title("💰 Doanh thu")

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
        JOIN rooms r ON b.room_id = r.id
        WHERE b.status != 'Đã hủy'
        ORDER BY b.check_in DESC
    """)

    if revenue.empty:

        st.info("Chưa có dữ liệu doanh thu.")

    else:

        total_revenue = revenue["Doanh thu"].sum()

        completed_revenue = revenue[
            revenue["Trạng thái"] == "Đã trả phòng"
        ]["Doanh thu"].sum()

        staying_revenue = revenue[
            revenue["Trạng thái"] == "Đang ở"
        ]["Doanh thu"].sum()

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "💰 Tổng doanh thu",
            format_currency(total_revenue)
        )

        col2.metric(
            "🚪 Đã trả phòng",
            format_currency(completed_revenue)
        )

        col3.metric(
            "🏨 Đang lưu trú",
            format_currency(staying_revenue)
        )

        st.divider()

        st.subheader("📊 Doanh thu theo loại phòng")

        revenue_by_type = query_df("""
            SELECT
                r.room_type AS "Loại phòng",
                SUM(b.total_amount) AS "Doanh thu"
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
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

        st.subheader("📑 Chi tiết doanh thu")

        st.dataframe(
            revenue,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Doanh thu": st.column_config.NumberColumn(
                    format="%d ₫"
                )
            }
        )


# =========================================================
# CÀI ĐẶT
# =========================================================

elif menu == "⚙️ Cài đặt":

    st.title("⚙️ Cài đặt")

    st.subheader("🏨 Thông tin hệ thống")

    st.text_input(
        "Tên khách sạn",
        value="My Hotel",
        key="hotel_name"
    )

    st.text_input(
        "Địa chỉ",
        value="Việt Nam",
        key="hotel_address"
    )

    st.text_input(
        "Số điện thoại",
        value="0123 456 789",
        key="hotel_phone"
    )

    st.divider()

    st.subheader("🗄️ Database")

    st.info(
        "Dữ liệu được lưu trong file "
        "`hotel.db` nằm cùng thư mục với `app.py`."
    )

    st.warning(
        "Không xóa file hotel.db nếu bạn muốn giữ dữ liệu."
    )

    st.divider()

    st.subheader("📌 Thống kê database")

    rooms_count = query_df(
        "SELECT COUNT(*) AS count FROM rooms"
    ).iloc[0]["count"]

    bookings_count = query_df(
        "SELECT COUNT(*) AS count FROM bookings"
    ).iloc[0]["count"]

    c1, c2 = st.columns(2)

    c1.metric(
        "Số phòng",
        rooms_count
    )

    c2.metric(
        "Số lượt đặt phòng",
        bookings_count
    )

    st.divider()

    st.caption(
        "Hotel Manager • Streamlit • SQLite"
    )
