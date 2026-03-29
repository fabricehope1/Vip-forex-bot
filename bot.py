import requests, asyncio
from datetime import datetime, timedelta
from telegram import *
from telegram.ext import *
import os
TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8322336050
CRYPTO = "0xA7123932DF237A24ad8c251502C169d744dd6D41"

users=set()
vip_users={ADMIN_ID}
pending={}
broadcast_mode={}

wins=0
losses=0

# ===== SAFE REQUEST =====
def get_price(pair):
    try:
        url=f"https://api.exchangerate-api.com/v4/latest/{pair[:3]}"
        data=requests.get(url,timeout=10).json()
        return data["rates"][pair[3:]]
    except:
        return None

# ===== ANALYSIS =====
def analyze(pair):
    price=get_price(pair)
    if not price:
        return None,None

    val=int(price*10000)%10
    signal="BUY 📈" if val>=5 else "SELL 📉"

    return signal,price

# ===== START =====
async def start(update,context):
    users.add(update.effective_user.id)

    keyboard=[
        ["📊 Get Signal","💎 VIP"],
        ["👑 Admin Panel"]
    ]

    await update.message.reply_text(
        "🔥 TRADING BOT READY",
        reply_markup=ReplyKeyboardMarkup(keyboard,resize_keyboard=True)
    )

# ===== PAIR =====
async def pair_menu(update,context):
    keyboard=[
        ["EURUSD","GBPUSD"],
        ["USDJPY"],
        ["🔙 Back"]
    ]
    await update.message.reply_text("Select Pair:",reply_markup=ReplyKeyboardMarkup(keyboard,resize_keyboard=True))

# ===== TIMEFRAME =====
async def timeframe_menu(update,context):
    context.user_data["pair"]=update.message.text

    keyboard=[
        ["1 MIN","3 MIN","5 MIN"],
        ["🔙 Back"]
    ]

    await update.message.reply_text("Select Timeframe:",reply_markup=ReplyKeyboardMarkup(keyboard,resize_keyboard=True))

# ===== SIGNAL =====
async def send_signal(update,context):
    uid=update.effective_user.id

    if uid not in vip_users and uid!=ADMIN_ID:
        await update.message.reply_text("❌ VIP only")
        return

    pair=context.user_data.get("pair")
    tf=update.message.text

    signal,entry=analyze(pair)

    if not signal:
        await update.message.reply_text("❌ Market error")
        return

    now=datetime.now()
    mins=int(tf.split()[0])

    entry_time=now.strftime("%H:%M:%S")
    expire_time=(now+timedelta(minutes=mins)).strftime("%H:%M:%S")

    await update.message.reply_text(f"""
📊 Pair: {pair}
⏱ TF: {tf}

🕒 Entry: {entry_time}
⌛ Expire: {expire_time}

🎯 Price: {entry}
📢 Signal: {signal}
""")

    asyncio.create_task(result(update,context,entry,pair,signal,mins))

# ===== RESULT =====
async def result(update,context,entry,pair,signal,mins):
    global wins,losses

    await asyncio.sleep(mins*60)

    new=get_price(pair)
    if not new:
        return

    if (signal=="BUY 📈" and new>entry) or (signal=="SELL 📉" and new<entry):
        wins+=1
        res="WIN ✅"
    else:
        losses+=1
        res="LOSS ❌"

    await context.bot.send_message(update.effective_chat.id,f"📊 RESULT: {res}")

# ===== VIP =====
async def vip(update,context):
    pending[update.effective_user.id]=True
    await update.message.reply_text(
        f"💰 PAY:\n`{CRYPTO}`\nSend screenshot",
        parse_mode="Markdown"
    )

# ===== SCREENSHOT =====
async def photo(update,context):
    uid=update.effective_user.id

    if uid in pending:
        await context.bot.send_photo(
            ADMIN_ID,
            update.message.photo[-1].file_id,
            caption=f"User: {uid}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve",callback_data=f"a_{uid}")],
                [InlineKeyboardButton("❌ Reject",callback_data=f"r_{uid}")]
            ])
        )

        await update.message.reply_text("⏳ Waiting approval")

# ===== ADMIN APPROVE =====
async def admin_action(update,context):
    q=update.callback_query
    uid=int(q.data.split("_")[1])

    if "a_" in q.data:
        vip_users.add(uid)
        await context.bot.send_message(uid,"✅ VIP ACTIVE")
    else:
        await context.bot.send_message(uid,"❌ REJECTED")

    await q.answer()
    await q.edit_message_text("Done")

# ===== ADMIN PANEL =====
async def admin_panel(update,context):
    if update.effective_user.id!=ADMIN_ID:
        return

    keyboard=[
        ["📢 Broadcast","📊 Stats"],
        ["➕ Add VIP","➖ Remove VIP"],
        ["🔙 Back"]
    ]

    await update.message.reply_text("👑 ADMIN PANEL",reply_markup=ReplyKeyboardMarkup(keyboard,resize_keyboard=True))

# ===== BROADCAST =====
async def broadcast(update,context):
    uid=update.effective_user.id
    if uid!=ADMIN_ID:
        return

    broadcast_mode[uid]=True
    await update.message.reply_text("📢 Broadcast ON\nSend anything\nType STOP to exit")

# ===== STATS =====
async def stats(update,context):
    await update.message.reply_text(f"""
👥 Users: {len(users)}
💎 VIP: {len(vip_users)}

🏆 WIN: {wins}
❌ LOSS: {losses}
""")

# ===== ADD VIP =====
async def add_vip(update,context):
    context.user_data["addvip"]=True
    await update.message.reply_text("Send User ID")

# ===== REMOVE VIP =====
async def remove_vip(update,context):
    context.user_data["removevip"]=True
    await update.message.reply_text("Send User ID")

# ===== HANDLE =====
async def handle(update,context):
    uid=update.effective_user.id
    text=update.message.text if update.message.text else ""

    # ADD VIP
    if context.user_data.get("addvip") and uid==ADMIN_ID:
        try:
            vip_users.add(int(text))
            await update.message.reply_text("✅ VIP ADDED")
        except:
            await update.message.reply_text("❌ INVALID")
        context.user_data["addvip"]=False
        return

    # REMOVE VIP
    if context.user_data.get("removevip") and uid==ADMIN_ID:
        try:
            vip_users.discard(int(text))
            await update.message.reply_text("❌ VIP REMOVED")
        except:
            await update.message.reply_text("ERROR")
        context.user_data["removevip"]=False
        return

    # BROADCAST LOOP
    if broadcast_mode.get(uid) and uid==ADMIN_ID:

        if text=="STOP":
            broadcast_mode[uid]=False
            await update.message.reply_text("❌ Broadcast stopped")
            return

        for u in users:
            try:
                if update.message.text:
                    await context.bot.send_message(u,text)
                elif update.message.photo:
                    await context.bot.send_photo(u,update.message.photo[-1].file_id,caption=update.message.caption or "")
                elif update.message.video:
                    await context.bot.send_video(u,update.message.video.file_id,caption=update.message.caption or "")
            except:
                pass
        return

    # BUTTONS
    if text=="📊 Get Signal":
        await pair_menu(update,context)

    elif text in ["EURUSD","GBPUSD","USDJPY"]:
        await timeframe_menu(update,context)

    elif text in ["1 MIN","3 MIN","5 MIN"]:
        await send_signal(update,context)

    elif text=="💎 VIP":
        await vip(update,context)

    elif text=="👑 Admin Panel":
        await admin_panel(update,context)

    elif text=="📢 Broadcast":
        await broadcast(update,context)

    elif text=="📊 Stats":
        await stats(update,context)

    elif text=="➕ Add VIP":
        await add_vip(update,context)

    elif text=="➖ Remove VIP":
        await remove_vip(update,context)

    elif text=="🔙 Back":
        await start(update,context)

# ===== MAIN =====
def main():
    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(MessageHandler(filters.PHOTO,photo))
    app.add_handler(MessageHandler(filters.ALL,handle))
    app.add_handler(CallbackQueryHandler(admin_action))

    print("🔥 BOT RUNNING PERFECTLY")
    app.run_polling()

if __name__=="__main__":
    main()
