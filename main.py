
import telebot
from telebot import types
import sqlite3
import threading
import time
from datetime import datetime
# ========= إعدادات =========
TOKEN = "8979389438:AAElu4h6HreASjk2MAvfrNX037OxILVqhZo "
OWNER_ID = 8379531283
bot = telebot.TeleBot(TOKEN)
# ========= قاعدة بيانات =========
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()
# إنشاء الجداول إذا لم تكن موجودة
cur.execute("""CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
points INTEGER DEFAULT 0,
join_date TEXT,
last_active TEXT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS admins(
user_id INTEGER PRIMARY KEY,
added_by INTEGER,
added_date TEXT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS numbers(
id INTEGER PRIMARY KEY AUTOINCREMENT,
number TEXT UNIQUE,
code TEXT,
price INTEGER DEFAULT 10,
service TEXT DEFAULT 'عام',
added_by INTEGER,
added_date TEXT,
status TEXT DEFAULT 'متاح'
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS history(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
number TEXT,
code TEXT,
price INTEGER,
purchase_date TEXT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS recharge_requests(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
amount INTEGER,
proof TEXT,
status TEXT DEFAULT 'معلق',
request_date TEXT
)""")
conn.commit()
# ========= إصلاح الأعمدة المفقودة =========
def ensure_column(table, column, col_type="INTEGER", default=None):
try:
cur.execute(f"PRAGMA table_info({table})")
columns = [r[1] for r in cur.fetchall()]
if column not in columns:
if default is not None:
cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}")
else:
cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
conn.commit()
print(f"✅ تم إضافة العمود {column} إلى الجدول {table}")
return True
return True
except Exception as e:
print(f"❌ خطأ في إضافة العمود {column}: {e}")
return False
# تأكد من وجود جميع الأعمدة مع القيم الافتراضية
def initialize_columns():
# إضافة الأعمدة بدون DEFAULT المعقد
ensure_column("users", "points", "INTEGER", 0)
ensure_column("users", "join_date", "TEXT")
ensure_column("users", "last_active", "TEXT")
ensure_column("numbers", "price", "INTEGER", 10)
ensure_column("numbers", "service", "TEXT", "'عام'")
ensure_column("numbers", "added_by", "INTEGER")
ensure_column("numbers", "added_date", "TEXT")
ensure_column("numbers", "status", "TEXT", "'متاح'")
ensure_column("history", "price", "INTEGER", 0)
ensure_column("history", "purchase_date", "TEXT")
ensure_column("admins", "added_by", "INTEGER")
ensure_column("admins", "added_date", "TEXT")
# تهيئة البيانات القديمة
try:
cur.execute("UPDATE users SET join_date = ? WHERE join_date IS NULL", (get_current_time(),))
cur.execute("UPDATE users SET last_active = ? WHERE last_active IS NULL", (get_current_time(),))
cur.execute("UPDATE numbers SET service = 'عام' WHERE service IS NULL")
cur.execute("UPDATE numbers SET status = 'متاح' WHERE status IS NULL")
conn.commit()
except Exception as e:
print(f"❌ خطأ في تهيئة البيانات: {e}")
# تهيئة الأعمدة
initialize_columns()
# ========= دوال مساعدة =========
def is_admin(uid):
if uid == OWNER_ID:
return True
cur.execute("SELECT * FROM admins WHERE user_id=?", (uid,))
return cur.fetchone() is not None
def add_points_to_user(uid, amount):
try:
cur.execute("INSERT OR IGNORE INTO users(user_id, points, join_date, last_active) VALUES(?,?,?,?)",
(uid, 0, get_current_time(), get_current_time()))
cur.execute("UPDATE users SET points=points+?, last_active=? WHERE user_id=?", (amount, get_current_time(), uid))
conn.commit()
return True
except Exception as e:
print(f"❌ خطأ في إضافة النقاط: {e}")
return False
def remove_points_from_user(uid, amount):
try:
cur.execute("INSERT OR IGNORE INTO users(user_id, points, join_date, last_active) VALUES(?,?,?,?)",
(uid, 0, get_current_time(), get_current_time()))
cur.execute("UPDATE users SET points=points-?, last_active=? WHERE user_id=?", (amount, get_current_time(), uid))
conn.commit()
return True
except Exception as e:
print(f"❌ خطأ في خصم النقاط: {e}")
return False
def get_user_points(uid):
try:
cur.execute("SELECT points FROM users WHERE user_id=?", (uid,))
row = cur.fetchone()
return row[0] if row else 0
except:
return 0
def get_current_time():
return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def update_user_activity(uid):
try:
cur.execute("INSERT OR IGNORE INTO users(user_id, points, join_date, last_active) VALUES(?,?,?,?)",
(uid, 0, get_current_time(), get_current_time()))
cur.execute("UPDATE users SET last_active=? WHERE user_id=?", (get_current_time(), uid))
conn.commit()
except Exception as e:
print(f"❌ خطأ في تحديث النشاط: {e}")
# ========= /start =========
@bot.message_handler(commands=["start"])
def start(msg):
uid = msg.from_user.id
update_user_activity(uid)
kb = types.InlineKeyboardMarkup(row_width=2)
kb.add(
types.InlineKeyboardButton("🎯 شراء رقم", callback_data="buy"),
types.InlineKeyboardButton("💰 رصيدي", callback_data="points")
)
kb.add(
types.InlineKeyboardButton("🔄 شحن الرصيد", callback_data="recharge"),
types.InlineKeyboardButton("📊 إحصائياتي", callback_data="mystats")
)
kb.add(
types.InlineKeyboardButton("📞 دعم فني", url=SUPPORT)
)
if is_admin(uid):
kb.add(types.InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel"))
welcome_text = """
👋 أهلاً بك في بوت شراء الأرقام بالنقاط
🎯 **المميزات:**
• شراء أرقام متنوعة بسهولة
• نظام نقاط مرن
• دعم فني متواصل
• واجهة سهلة الاستخدام
اختر من القائمة:
"""
try:
bot.send_message(uid, welcome_text, reply_markup=kb, parse_mode="Markdown")
except Exception as e:
print(f"❌ خطأ في إرسال رسالة البداية: {e}")
# ========= أزرار المستخدم =========
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
uid = call.from_user.id
update_user_activity(uid)
if call.data == "points":
points = get_user_points(uid)
try:
bot.answer_callback_query(call.id, f"💰 رصيدك: {points} نقطة")
except:
pass
elif call.data == "mystats":
try:
cur.execute("SELECT points, join_date FROM users WHERE user_id=?", (uid,))
user_data = cur.fetchone()
cur.execute("SELECT COUNT(*) FROM history WHERE user_id=?", (uid,))
purchases_result = cur.fetchone()
purchases = purchases_result[0] if purchases_result else 0
if user_data:
stats_text = f"""
📊 **إحصائياتك الشخصية:**
💰 الرصيد: {user_data[0]} نقطة
🛒 عدد المشتريات: {purchases} مرة
📅 تاريخ الانضمام: {user_data[1][:10] if user_data[1] else 'غير محدد'}
"""
else:
stats_text = "❌ لا توجد بيانات عنك في النظام"
bot.edit_message_text(stats_text, uid, call.message.message_id, parse_mode="Markdown")
except Exception as e:
try:
bot.answer_callback_query(call.id, "❌ حدث خطأ في جلب البيانات")
except:
pass
elif call.data == "buy":
show_categories(uid, call.message.message_id)
elif call.data.startswith("cat_"):
category = call.data.split("_")[1]
show_numbers(uid, call.message.message_id, category)
elif call.data.startswith("buy_"):
num_id = int(call.data.split("_")[1])
purchase_number(uid, num_id, call.message.message_id, call.id)
elif call.data == "recharge":
show_recharge_options(uid, call.message.message_id)
elif call.data.startswith("recharge_"):
amount = int(call.data.split("_")[1])
request_recharge(uid, amount, call.message.message_id)
elif call.data == "admin_panel":
if is_admin(uid):
show_admin_panel(uid, call.message.message_id)
else:
try:
bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية للوصول لهذه اللوحة")
except:
pass
elif call.data.startswith("admin_"):
if is_admin(uid):
handle_admin_actions(uid, call.data, call.message.message_id, call.id)
else:
try:
bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
except:
pass
elif call.data == "main_menu":
# إعادة إنشاء رسالة البداية
try:
bot.delete_message(uid, call.message.message_id)
except:
pass
start(call.message)
elif call.data == "help":
help_text = f"""
ℹ️ **كيفية استخدام البوت:**
1. 🎯 **شراء رقم:** اختر من الأقسام ثم اختر الرقم المناسب
2. 💰 **شحن الرصيد:** اختر المبلغ ثم تواصل مع الدعم
3. 📊 **متابعة المشتريات:** يمكنك رؤية سجل مشترياتك
📞 للاستفسارات: @J_D_D_M
"""
try:
bot.edit_message_text(help_text, uid, call.message.message_id, parse_mode="Markdown")
except:
pass
# معالجة الأزرار الجديدة
elif call.data == "add_number_menu":
msg = bot.send_message(uid, "📝 أرسل الرقم بالصيغة:\nالرقم | الكود | السعر | القسم\nمثال: 07701234567 | ABC123 | 50 | فيسبوك")
bot.register_next_step_handler(msg, process_add_number)
elif call.data == "delete_number_menu":
msg = bot.send_message(uid, "🗑️ أرسل ID الرقم الذي تريد حذفه:")
bot.register_next_step_handler(msg, process_delete_number)
elif call.data == "list_numbers":
show_all_numbers(uid, call.message.message_id)
elif call.data == "edit_price_menu":
msg = bot.send_message(uid, "✏️ أرسل ID الرقم والسعر الجديد:\nمثال: 5 100")
bot.register_next_step_handler(msg, process_edit_price)
elif call.data == "add_admin_menu":
msg = bot.send_message(uid, "👤 أرسل ID المستخدم لإضافته كأدمن:")
bot.register_next_step_handler(msg, process_add_admin)
elif call.data == "remove_admin_menu":
msg = bot.send_message(uid, "🚫 أرسل ID الأدمن الذي تريد إزالته:")
bot.register_next_step_handler(msg, process_remove_admin)
elif call.data == "sales_log":
show_sales_log(uid, call.message.message_id)
elif call.data == "clean_data_menu":
clean_old_data(uid)
elif call.data == "admin_users":
show_users_management(uid, call.message.message_id)
elif call.data == "add_points_menu":
msg = bot.send_message(uid, "💰 أرسل ايدي المستخدم وعدد النقاط للإضافة:\nمثال: 123456789 100")
bot.register_next_step_handler(msg, process_add_points)
elif call.data == "remove_points_menu":
msg = bot.send_message(uid, "💸 أرسل ايدي المستخدم وعدد النقاط للخصم:\nمثال: 123456789 50")
bot.register_next_step_handler(msg, process_remove_points)
def show_categories(uid, message_id):
try:
cur.execute("SELECT DISTINCT service FROM numbers WHERE status='متاح'")
categories = cur.fetchall()
kb = types.InlineKeyboardMarkup(row_width=2)
buttons = []
for cat in categories:
buttons.append(types.InlineKeyboardButton(f"📱 {cat[0]}", callback_data=f"cat_{cat[0]}"))
# ترتيب الأزرار في صفوف
for i in range(0, len(buttons), 2):
if i + 1 < len(buttons):
kb.add(buttons[i], buttons[i + 1])
else:
kb.add(buttons[i])
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
bot.edit_message_text("📋 اختر القسم:", uid, message_id, reply_markup=kb)
except Exception as e:
try:
bot.edit_message_text("❌ حدث خطأ في تحميل الأقسام", uid, message_id)
except:
pass
def show_numbers(uid, message_id, category):
try:
cur.execute("SELECT id, number, price FROM numbers WHERE service=? AND status='متاح' ORDER BY price", (category,))
numbers = cur.fetchall()
if not numbers:
kb = types.InlineKeyboardMarkup()
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="buy"))
bot.edit_message_text("❌ لا توجد أرقام متاحة في هذا القسم حالياً", uid, message_id, reply_markup=kb)
return
kb = types.InlineKeyboardMarkup(row_width=2)
buttons = []
for num in numbers:
buttons.append(types.InlineKeyboardButton(f"{num[1]} - {num[2]} نقطة", callback_data=f"buy_{num[0]}"))
for i in range(0, len(buttons), 2):
if i + 1 < len(buttons):
kb.add(buttons[i], buttons[i + 1])
else:
kb.add(buttons[i])
kb.add(types.InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="buy"))
bot.edit_message_text(f"📱 أرقام قسم {category}:\n\n💡 اختر الرقم المناسب:", uid, message_id, reply_markup=kb)
except Exception as e:
try:
bot.edit_message_text("❌ حدث خطأ في تحميل الأرقام", uid, message_id)
except:
pass
def purchase_number(uid, num_id, message_id, callback_id):
try:
cur.execute("SELECT number, code, price FROM numbers WHERE id=?", (num_id,))
number_data = cur.fetchone()
if not number_data:
try:
bot.answer_callback_query(callback_id, "❌ هذا الرقم غير متوفر حالياً")
except:
pass
return
number, code, price = number_data
user_points = get_user_points(uid)
if user_points < price:
try:
bot.answer_callback_query(callback_id, f"❌ رصيدك غير كافي. تحتاج {price} نقطة")
except:
pass
return
# إتمام عملية الشراء
if remove_points_from_user(uid, price):
cur.execute("DELETE FROM numbers WHERE id=?", (num_id,))
cur.execute("INSERT INTO history(user_id, number, code, price, purchase_date) VALUES(?,?,?,?,?)",
(uid, number, code, price, get_current_time()))
conn.commit()
success_text = f"""
✅ **تم الشراء بنجاح!**
📱 **الرقم:** `{number}`
🔑 **الكود:** `{code}`
💵 **السعر:** {price} نقطة
💰 **رصيدك المتبقي:** {get_user_points(uid)} نقطة
📞 للاستفسارات: @J_D_D_M
"""
try:
bot.edit_message_text(success_text, uid, message_id, parse_mode="Markdown")
# إرسال رسالة تأكيد منفصلة
bot.send_message(uid, f"📦 تم إرسال التفاصيل:\n📱 الرقم: {number}\n🔑 الكود: {code}")
except:
pass
else:
try:
bot.answer_callback_query(callback_id, "❌ حدث خطأ في عملية الشراء")
except:
pass
except Exception as e:
try:
bot.answer_callback_query(callback_id, "❌ حدث خطأ في عملية الشراء")
except:
pass
def show_recharge_options(uid, message_id):
kb = types.InlineKeyboardMarkup(row_width=2)
amounts = [50, 100, 200, 500, 1000]
buttons = []
for amount in amounts:
buttons.append(types.InlineKeyboardButton(f"{amount} نقطة", callback_data=f"recharge_{amount}"))
for i in range(0, len(buttons), 2):
if i + 1 < len(buttons):
kb.add(buttons[i], buttons[i + 1])
else:
kb.add(buttons[i])
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
text = f"""
🔄 **شحن الرصيد**
اختر المبلغ المناسب أو راسل الدعم للمبالغ الأخرى:
💳 **طرق الدفع:**
• حوالة بنكية
• محافظ إلكترونية
• مدفوعات أخرى
📞 **الدعم:** @J_D_D_M
"""
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb, parse_mode="Markdown")
except:
pass
def request_recharge(uid, amount, message_id):
try:
cur.execute("INSERT INTO recharge_requests(user_id, amount, status, request_date) VALUES(?,?,?,?)",
(uid, amount, 'معلق', get_current_time()))
conn.commit()
request_id = cur.lastrowid
text = f"""
🔄 **تم تقديم طلب الشحن**
📋 **تفاصيل الطلب:**
💳 المبلغ: {amount} نقطة
🆔 رقم الطلب: {request_id}
⏳ الحالة: قيد المراجعة
📞 **راجع الدعم لإتمام العملية:** @J_D_D_M
🔢 **أرفق رقم الطلب عند التواصل**
"""
try:
bot.edit_message_text(text, uid, message_id, parse_mode="Markdown")
except:
pass
# إشعار للمشرفين
notify_admins(f"🔄 طلب شحن جديد:\n👤 المستخدم: {uid}\n💳 المبلغ: {amount} نقطة\n🆔 رقم الطلب: {request_id}")
except Exception as e:
try:
bot.edit_message_text("❌ حدث خطأ في تقديم الطلب", uid, message_id)
except:
pass
def show_admin_panel(uid, message_id):
kb = types.InlineKeyboardMarkup(row_width=2)
kb.add(
types.InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats"),
types.InlineKeyboardButton("📱 إدارة الأرقام", callback_data="admin_numbers")
)
kb.add(
types.InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users"),
types.InlineKeyboardButton("🔄 طلبات الشحن", callback_data="admin_recharge")
)
kb.add(
types.InlineKeyboardButton("💰 إدارة النقاط", callback_data="admin_points"),
types.InlineKeyboardButton("📢 بث رسالة", callback_data="admin_broadcast")
)
kb.add(
types.InlineKeyboardButton("⚙️ إعدادات متقدمة", callback_data="admin_advanced")
)
kb.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
text = "⚙️ **لوحة تحكم الأدمن**\n\nاختر الإدارة المناسبة:"
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb, parse_mode="Markdown")
except:
pass
def handle_admin_actions(uid, action, message_id, callback_id):
if action == "admin_stats":
show_admin_stats(uid, message_id)
elif action == "admin_numbers":
show_numbers_management(uid, message_id)
elif action == "admin_recharge":
show_recharge_requests(uid, message_id)
elif action == "admin_advanced":
show_advanced_settings(uid, message_id)
elif action == "admin_broadcast":
start_broadcast(uid, message_id)
elif action == "admin_users":
show_users_management(uid, message_id)
elif action == "admin_points":
show_points_management(uid, message_id)
else:
try:
bot.answer_callback_query(callback_id, "⏳ قيد التطوير...")
except:
pass
def show_admin_stats(uid, message_id):
try:
cur.execute("SELECT COUNT(*) FROM users")
total_users = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = date('now')")
active_today_result = cur.fetchone()
active_today = active_today_result[0] if active_today_result else 0
cur.execute("SELECT COUNT(*) FROM numbers WHERE status='متاح'")
available_numbers_result = cur.fetchone()
available_numbers = available_numbers_result[0] if available_numbers_result else 0
cur.execute("SELECT COUNT(*) FROM history WHERE date(purchase_date) = date('now')")
today_sales_result = cur.fetchone()
today_sales = today_sales_result[0] if today_sales_result else 0
cur.execute("SELECT SUM(price) FROM history WHERE date(purchase_date) = date('now')")
today_revenue_result = cur.fetchone()
today_revenue = today_revenue_result[0] if today_revenue_result and today_revenue_result[0] else 0
cur.execute("SELECT COUNT(*) FROM recharge_requests WHERE status='معلق'")
pending_requests_result = cur.fetchone()
pending_requests = pending_requests_result[0] if pending_requests_result else 0
stats_text = f"""
📊 **إحصائيات البوت**
👥 **المستخدمين:**
• إجمالي المستخدمين: {total_users}
• النشطين اليوم: {active_today}
📱 **الأرقام:**
• الأرقام المتاحة: {available_numbers}
💰 **المبيعات:**
• مبيعات اليوم: {today_sales}
• إيرادات اليوم: {today_revenue} نقطة
🔄 **طلبات الشحن:**
• الطلبات المعلقة: {pending_requests}
"""
kb = types.InlineKeyboardMarkup()
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
try:
bot.edit_message_text(stats_text, uid, message_id, reply_markup=kb, parse_mode="Markdown")
except:
pass
except Exception as e:
try:
bot.edit_message_text("❌ حدث خطأ في جلب الإحصائيات", uid, message_id)
except:
pass
def show_numbers_management(uid, message_id):
kb = types.InlineKeyboardMarkup(row_width=2)
kb.add(
types.InlineKeyboardButton("➕ إضافة رقم", callback_data="add_number_menu"),
types.InlineKeyboardButton("🗑️ حذف رقم", callback_data="delete_number_menu")
)
kb.add(
types.InlineKeyboardButton("📋 عرض الأرقام", callback_data="list_numbers"),
types.InlineKeyboardButton("✏️ تعديل سعر", callback_data="edit_price_menu")
)
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
text = "📱 **إدارة الأرقام**\n\nاختر العملية المطلوبة:"
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb, parse_mode="Markdown")
except:
pass
def show_points_management(uid, message_id):
kb = types.InlineKeyboardMarkup(row_width=2)
kb.add(
types.InlineKeyboardButton("💰 إضافة نقاط", callback_data="add_points_menu"),
types.InlineKeyboardButton("💸 خصم نقاط", callback_data="remove_points_menu")
)
kb.add(
types.InlineKeyboardButton("📊 عرض رصيد مستخدم", callback_data="show_user_points"),
types.InlineKeyboardButton("📈 إحصائيات النقاط", callback_data="points_stats")
)
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
text = "💰 **إدارة النقاط**\n\nاختر العملية المطلوبة:"
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb, parse_mode="Markdown")
except:
pass
def show_recharge_requests(uid, message_id):
try:
cur.execute("""
SELECT r.id, r.user_id, r.amount, r.request_date
FROM recharge_requests r
WHERE r.status='معلق'
ORDER BY r.request_date
""")
requests = cur.fetchall()
if not requests:
text = "✅ لا توجد طلبات شحن معلقة"
else:
text = "🔄 **طلبات الشحن المعلقة:**\n\n"
for req in requests:
text += f"🆔 {req[0]} | 👤 {req[1]} | 💰 {req[2]} | 📅 {req[3][:16] if req[3] else 'غير محدد'}\n"
kb = types.InlineKeyboardMarkup()
kb.add(types.InlineKeyboardButton("🔄 تحديث", callback_data="admin_recharge"))
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb)
except:
pass
except Exception as e:
try:
bot.edit_message_text("❌ حدث خطأ في جلب الطلبات", uid, message_id)
except:
pass
def show_advanced_settings(uid, message_id):
kb = types.InlineKeyboardMarkup(row_width=2)
kb.add(
types.InlineKeyboardButton("👤 إضافة أدمن", callback_data="add_admin_menu"),
types.InlineKeyboardButton("🚫 حذف أدمن", callback_data="remove_admin_menu")
)
kb.add(
types.InlineKeyboardButton("📜 سجل المبيعات", callback_data="sales_log"),
types.InlineKeyboardButton("🧹 تنظيف البيانات", callback_data="clean_data_menu")
)
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
text = "⚙️ **الإعدادات المتقدمة**\n\nاختر العملية المطلوبة:"
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb, parse_mode="Markdown")
except:
pass
def show_users_management(uid, message_id):
try:
cur.execute("SELECT user_id, points, last_active FROM users ORDER BY last_active DESC LIMIT 20")
users = cur.fetchall()
text = "👥 **آخر 20 مستخدم نشط:**\n\n"
for user in users:
text += f"🆔 {user[0]} | 💰 {user[1]} | 📅 {user[2][:16] if user[2] else 'غير محدد'}\n"
kb = types.InlineKeyboardMarkup()
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb)
except:
pass
except Exception as e:
try:
bot.edit_message_text("❌ حدث خطأ في جلب المستخدمين", uid, message_id)
except:
pass
def start_broadcast(uid, message_id):
try:
msg = bot.send_message(uid, "📢 **أرسل الرسالة للبث الجماعي:**\n\n(يمكنك استخدام Markdown)", parse_mode="Markdown")
bot.register_next_step_handler(msg, process_broadcast)
except:
pass
def process_broadcast(msg):
text = msg.text
uid = msg.from_user.id
if not is_admin(uid):
return
try:
bot.send_message(uid, "⏳ جاري إرسال الرسالة لجميع المستخدمين...")
except:
pass
cur.execute("SELECT user_id FROM users")
users = cur.fetchall()
sent = 0
failed = 0
for user in users:
try:
bot.send_message(user[0], text, parse_mode="Markdown")
sent += 1
time.sleep(0.1)  # تجنب حظر التيليجرام
except:
failed += 1
try:
bot.send_message(uid, f"✅ **تم الانتهاء من البث:**\n\n✅ تم الإرسال: {sent}\n❌ فشل الإرسال: {failed}")
except:
pass
# ========= دوال جديدة للإدارة =========
def process_add_number(msg):
uid = msg.from_user.id
try:
parts = msg.text.split('|')
if len(parts) >= 3:
number = parts[0].strip()
code = parts[1].strip()
price = int(parts[2].strip())
service = parts[3].strip() if len(parts) > 3 else "عام"
cur.execute("INSERT INTO numbers(number, code, price, service, added_by, added_date) VALUES(?,?,?,?,?,?)",
(number, code, price, service, uid, get_current_time()))
conn.commit()
bot.send_message(uid, f"✅ تم إضافة الرقم {number} بنجاح بسعر {price} نقطة")
else:
bot.send_message(uid, "❌ الصيغة غير صحيحة. استخدم: الرقم | الكود | السعر | القسم")
except Exception as e:
bot.send_message(uid, f"❌ حدث خطأ: {e}")
def process_delete_number(msg):
uid = msg.from_user.id
try:
num_id = int(msg.text.strip())
cur.execute("SELECT number FROM numbers WHERE id=?", (num_id,))
result = cur.fetchone()
if result:
cur.execute("DELETE FROM numbers WHERE id=?", (num_id,))
conn.commit()
bot.send_message(uid, f"✅ تم حذف الرقم {result[0]} بنجاح")
else:
bot.send_message(uid, "❌ لا يوجد رقم بهذا ID")
except:
bot.send_message(uid, "❌ أدخل ID صحيح")
def show_all_numbers(uid, message_id):
try:
cur.execute("SELECT id, number, price, service FROM numbers WHERE status='متاح' ORDER BY service, price")
numbers = cur.fetchall()
if not numbers:
text = "❌ لا توجد أرقام متاحة حالياً"
else:
text = "📋 **جميع الأرقام المتاحة:**\n\n"
for num in numbers:
text += f"🆔 {num[0]} | 📱 {num[1]} | 💰 {num[2]} | 📁 {num[3]}\n"
kb = types.InlineKeyboardMarkup()
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_numbers"))
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb)
except:
pass
except Exception as e:
try:
bot.edit_message_text("❌ حدث خطأ في جلب الأرقام", uid, message_id)
except:
pass
def process_edit_price(msg):
uid = msg.from_user.id
try:
parts = msg.text.split()
if len(parts) >= 2:
num_id = int(parts[0])
new_price = int(parts[1])
cur.execute("UPDATE numbers SET price=? WHERE id=?", (new_price, num_id))
conn.commit()
bot.send_message(uid, f"✅ تم تحديث سعر الرقم إلى {new_price} نقطة")
else:
bot.send_message(uid, "❌ استخدم: ID_الرقم السعر_الجديد")
except:
bot.send_message(uid, "❌ أدخل بيانات صحيحة")
def process_add_admin(msg):
uid = msg.from_user.id
try:
new_admin_id = int(msg.text.strip())
cur.execute("INSERT OR IGNORE INTO admins(user_id, added_by, added_date) VALUES(?,?,?)", (new_admin_id, uid, get_current_time()))
conn.commit()
bot.send_message(uid, f"✅ تم إضافة المستخدم {new_admin_id} كأدمن")
except:
bot.send_message(uid, "❌ أدخل ID صحيح")
def process_remove_admin(msg):
uid = msg.from_user.id
try:
admin_id = int(msg.text.strip())
if admin_id == OWNER_ID:
bot.send_message(uid, "❌ لا يمكن حذف المطور الأساسي")
return
cur.execute("DELETE FROM admins WHERE user_id=?", (admin_id,))
conn.commit()
bot.send_message(uid, f"✅ تم حذف الأدمن {admin_id}")
except:
bot.send_message(uid, "❌ أدخل ID صحيح")
def process_add_points(msg):
uid = msg.from_user.id
try:
parts = msg.text.split()
if len(parts) >= 2:
user_id = int(parts[0])
points = int(parts[1])
if add_points_to_user(user_id, points):
current_points = get_user_points(user_id)
bot.send_message(uid, f"✅ تم إضافة {points} نقطة للمستخدم {user_id}\n💰 الرصيد الحالي: {current_points} نقطة")
# إشعار للمستخدم
try:
bot.send_message(user_id, f"🎉 تم إضافة {points} نقطة إلى رصيدك\n💰 رصيدك الحالي: {current_points} نقطة")
except:
pass
else:
bot.send_message(uid, "❌ فشل في إضافة النقاط")
else:
bot.send_message(uid, "❌ استخدم: ايدي_المستخدم عدد_النقاط")
except:
bot.send_message(uid, "❌ أدخل بيانات صحيحة")
def process_remove_points(msg):
uid = msg.from_user.id
try:
parts = msg.text.split()
if len(parts) >= 2:
user_id = int(parts[0])
points = int(parts[1])
current_points = get_user_points(user_id)
if current_points < points:
bot.send_message(uid, f"❌ رصيد المستخدم غير كافي. الرصيد الحالي: {current_points} نقطة")
return
if remove_points_from_user(user_id, points):
new_points = get_user_points(user_id)
bot.send_message(uid, f"✅ تم خصم {points} نقطة من المستخدم {user_id}\n💰 الرصيد الحالي: {new_points} نقطة")
# إشعار للمستخدم
try:
bot.send_message(user_id, f"⚠️ تم خصم {points} نقطة من رصيدك\n💰 رصيدك الحالي: {new_points} نقطة")
except:
pass
else:
bot.send_message(uid, "❌ فشل في خصم النقاط")
else:
bot.send_message(uid, "❌ استخدم: ايدي_المستخدم عدد_النقاط")
except:
bot.send_message(uid, "❌ أدخل بيانات صحيحة")
def show_sales_log(uid, message_id):
try:
cur.execute("""
SELECT h.id, h.user_id, h.number, h.price, h.purchase_date
FROM history h
ORDER BY h.purchase_date DESC
LIMIT 20
""")
sales = cur.fetchall()
if not sales:
text = "❌ لا توجد مبيعات حتى الآن"
else:
text = "📜 **سجل آخر 20 عملية بيع:**\n\n"
for sale in sales:
text += f"🆔 {sale[0]} | 👤 {sale[1]} | 📱 {sale[2]} | 💰 {sale[3]} | 📅 {sale[4][:16] if sale[4] else 'غير محدد'}\n"
kb = types.InlineKeyboardMarkup()
kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_advanced"))
try:
bot.edit_message_text(text, uid, message_id, reply_markup=kb)
except:
pass
except Exception as e:
try:
bot.edit_message_text("❌ حدث خطأ في جلب سجل المبيعات", uid, message_id)
except:
pass
def clean_old_data(uid):
try:
# حذف المستخدمين غير النشطين منذ أكثر من 30 يوم
cur.execute("DELETE FROM users WHERE last_active < datetime('now', '-30 days')")
deleted_users = cur.rowcount
# حذف طلبات الشحن المكتملة القديمة
cur.execute("DELETE FROM recharge_requests WHERE status='مكتمل' AND request_date < datetime('now', '-7 days')")
deleted_requests = cur.rowcount
conn.commit()
bot.send_message(uid, f"🧹 **تم تنظيف البيانات:**\n\n👥 المستخدمين المحذوفين: {deleted_users}\n🔄 طلبات الشحن المحذوفة: {deleted_requests}")
except Exception as e:
bot.send_message(uid, f"❌ حدث خطأ في تنظيف البيانات: {e}")
def notify_admins(message):
try:
cur.execute("SELECT user_id FROM admins")
admins = cur.fetchall()
all_admins = [admin[0] for admin in admins]
all_admins.append(OWNER_ID)
for admin_id in all_admins:
try:
bot.send_message(admin_id, message)
except:
pass
except:
pass
# ========= الأوامر النصية للمشرفين =========
@bot.message_handler(commands=["admin"])
def admin_command(msg):
uid = msg.from_user.id
if is_admin(uid):
show_admin_panel(uid, msg.message_id)
else:
bot.send_message(uid, "❌ ليس لديك صلاحية الوصول لهذا الأمر")
@bot.message_handler(commands=["points"])
def points_command(msg):
uid = msg.from_user.id
points = get_user_points(uid)
bot.send_message(uid, f"💰 رصيدك الحالي: {points} نقطة")
@bot.message_handler(commands=["stats"])
def stats_command(msg):
uid = msg.from_user.id
if is_admin(uid):
show_admin_stats(uid, msg.message_id)
else:
try:
cur.execute("SELECT points, join_date FROM users WHERE user_id=?", (uid,))
user_data = cur.fetchone()
cur.execute("SELECT COUNT(*) FROM history WHERE user_id=?", (uid,))
purchases_result = cur.fetchone()
purchases = purchases_result[0] if purchases_result else 0
if user_data:
stats_text = f"""
📊 **إحصائياتك:**
💰 الرصيد: {user_data[0]} نقطة
🛒 عدد المشتريات: {purchases} مرة
📅 تاريخ الانضمام: {user_data[1][:10] if user_data[1] else 'غير محدد'}
"""
else:
stats_text = "❌ لا توجد بيانات عنك في النظام"
bot.send_message(uid, stats_text, parse_mode="Markdown")
except:
bot.send_message(uid, "❌ حدث خطأ في جلب الإحصائيات")
# ========= أوامر النصية للإدارة =========
@bot.message_handler(func=lambda m: is_admin(m.from_user.id))
def handle_admin_messages(msg):
uid = msg.from_user.id
text = msg.text.strip()
if text.startswith("اضف نقاط"):
try:
parts = text.split()
if len(parts) >= 3:
user_id = int(parts[1])
points = int(parts[2])
if add_points_to_user(user_id, points):
bot.send_message(uid, f"✅ تم إضافة {points} نقطة للمستخدم {user_id}")
else:
bot.send_message(uid, "❌ فشل في إضافة النقاط")
else:
bot.send_message(uid, "❌ استخدم: اضف نقاط [ايدي] [المبلغ]")
except:
bot.send_message(uid, "❌ خطأ في الصيغة")
elif text.startswith("خصم نقاط"):
try:
parts = text.split()
if len(parts) >= 3:
user_id = int(parts[1])
points = int(parts[2])
if remove_points_from_user(user_id, points):
bot.send_message(uid, f"✅ تم خصم {points} نقطة من المستخدم {user_id}")
else:
bot.send_message(uid, "❌ فشل في خصم النقاط")
else:
bot.send_message(uid, "❌ استخدم: خصم نقاط [ايدي] [المبلغ]")
except:
bot.send_message(uid, "❌ خطأ في الصيغة")
# ========= تشغيل البوت =========
def cleanup_old_data():
"""تنظيف البيانات القديمة بشكل دوري"""
while True:
try:
# حذف المستخدمين غير النشطين منذ أكثر من 30 يوم
cur.execute("DELETE FROM users WHERE last_active < datetime('now', '-30 days')")
# حذف طلبات الشحن المكتملة القديمة
cur.execute("DELETE FROM recharge_requests WHERE status='مكتمل' AND request_date < datetime('now', '-7 days')")
conn.commit()
except:
pass
time.sleep(24 * 60 * 60)  # انتظار 24 ساعة
# بدء عملية التنظيف في خيط منفصل
cleanup_thread = threading.Thread(target=cleanup_old_data, daemon=True)
cleanup_thread.start()
print("✅ البوت يعمل الآن ...")
try:
bot.polling(none_stop=True, interval=1)
except Exception as e:
print(f"❌ خطأ في تشغيل البوت: {e}")