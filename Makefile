.PHONY: start

install:
	cp yapo-scraper.service /etc/systemd/system/yapo-scraper.service
	cp yapo-scraper-telegram-bot.service /etc/systemd/system/yapo-scraper-telegram-bot.service
	cp yapo-scraper.timer /etc/systemd/system/yapo-scraper.timer
	cp yapo-scraper-telegram-bot.timer /etc/systemd/system/yapo-scraper-telegram-bot.timer

	systemctl enable yapo-scraper.timer
	systemctl enable yapo-scraper-telegram-bot.timer

start:
	systemctl start yapo-scraper.service
	systemctl start yapo-scraper-telegram-bot.service
