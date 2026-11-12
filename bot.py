
def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(60)
        .read_timeout(60)
        .write_timeout(60)
        .pool_timeout(60)
        .build()
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(answer_question, pattern=r"^answer:")
    )

    app.add_handler(
        CallbackQueryHandler(quick_answer, pattern=r"^quick:")
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    webhook_path = os.getenv("WEBHOOK_PATH")
    webhook_secret = os.getenv("WEBHOOK_SECRET")

    if not hostname or not webhook_path or not webhook_secret:
        raise ValueError("Render Webhook sozlamalari topilmadi!")

    port = int(os.getenv("PORT", "10000"))

    print("UZBEK GAMES WEBHOOK ISHGA TUSHMOQDA!", flush=True)

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path,
        webhook_url=f"https://{hostname}/{webhook_path}",
        secret_token=webhook_secret,
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
