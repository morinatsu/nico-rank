# -*- coding: utf-8 -*-
import os, re, datetime, StringIO, logging
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch

def db_retry(func):
    count = 0
    while count < 3:
        try:
            return func()
        except:
            count += 1
        else:
            raise datastore._ToDatastoreError()

#Rankingデータ
class Ranking(db.Model):
	date = db.DateProperty()
    											#日付
	rank = db.IntegerProperty()
												#RANK
	category_number = db.IntegerProperty()
												#カテゴリ番号
	category_name = db.StringProperty()
												#カテゴリ名
	title = db.StringProperty()
												#タイトル
	movie_url = db.LinkProperty()
												#URL
	sumnail_url = db.LinkProperty()
												#サムネイルURL

#基準日データ
class Relevant_date(db.Model):
	date = db.DateProperty()
    											#日付


class Report(webapp.RequestHandler):
	def get(self):

		#当日分のデータを削除
		def del_ranking():
			rankings = Ranking.gql("WHERE date = :date", date=create_date)
			for ranking in rankings:
				db_retry(ranking.delete())
			self.response.out.write(str(rankings.count()) + "records deleted")
  
		#データを変換
		def store_ranking(page_content):
			lines = StringIO.StringIO(page_content)
			count = 0
			r_line = re.compile(r"http://res.nimg.jp/img/_.gif")
			r_movie_url = re.compile("watch/sm[0-9]*")
			r_title_line = re.compile("class=\"watch")
			r_title = re.compile("href=\"watch/[a-z][a-z][0-9]*\">(?P<title>.*)</a></p>")
			r_sumnail_url = re.compile("http://tn-[a-z]*[0-9].smilevideo.jp/smile\?i=[0-9]*")
			for line in lines.readlines():
				#動画URL等をを含む行を取得
				if r_line.search(line):
					#RANKの取得
					rank = ( count // 6 ) + 1
					#カテゴリの取得
					category_number = count % 6
					if category_number == 0:
						category_name = u"エンタ・音楽・スポ"
					elif category_number == 1:
						category_name = u"教養・生活"
					elif category_number == 2:
						category_name = u"政治"
					elif category_number == 3:
						category_name = u"やってみた"
					elif category_number == 4:
						category_name = u"アニメ・ゲーム"
					elif category_number == 5:
						category_name = u"殿堂入りカテゴリ"
					#動画URLの取得
					m_movie_url = r_movie_url.search(line)
					if m_movie_url:
						movie_url = u"http://www.nicovideo.jp/" + m_movie_url.group().decode("utf-8")
					else:
						movie_url = u"http://www.nicovideo.jp/"
					#サムネイルURLの取得
					m_sumnail_url = r_sumnail_url.search(line)
					if m_sumnail_url:
						sumnail_url = m_sumnail_url.group().decode("utf-8")
					else:
						sumnail_url = u"http://www.nicovideo.jp/"
				#タイトルを含む行を取得
				if r_title_line.search(line):
					#タイトルの取得
					m_title = r_title.search(line)
					if m_title:
						title = m_title.group("title").decode("utf-8")
					else:
						title = u""
					#DataStoreへput
					ranking = Ranking(date=create_date,
										rank = rank,
										category_number = category_number,
										category_name = category_name,
										title = title,
										movie_url = movie_url,
										sumnail_url = sumnail_url)
					db_retry(ranking.put())
					count = count + 1
			self.response.out.write(datetime.datetime.now(JapanTZ()).strftime("%Y-%m-%d %H:%M:%S"))
			self.response.out.write(str(count) + "records inserted")
			return

		#基準日を更新する
		def update_relevant_date():
			relevant_date = Relevant_date(key_name="relevant_date",
											date=create_date)
			db_retry(relevant_date.put())

		#当日の日付取得
		create_date = datetime.datetime.now(JapanTZ()).date()
		#htmlをget
		page = urlfetch.fetch("http://www.nicovideo.jp/ranking")
		if page.status_code == 200:
			#当日分のデータが既にあれば削除
			del_ranking()
			#データを変換して保存
			store_ranking(page.content)
			#基準日を更新
			update_relevant_date()

class CSV(webapp.RequestHandler):
	def get(self):

		#日付の取得(dateパラメータの解釈、なければ当日)
		def get_date(date_string):
			#dateパラメータがあれば取得
			if date_string != "":
				# YYYYMMDD, YYYY-MM-DD, YYYY/MM/DD
				date_match = re.match("^([0-9]{4})[-/]?([0-9]{2})[-/]?([0-9]{2})$",date_string)
				if date_match:
					year = int(date_match.group(1))
					month = int(date_match.group(2))
					day = int(date_match.group(3))
				else:
					# 日付として解釈できない（0件で返すために過去日付を設定）
					year = 1999
					month = 1	
					day = 1
					logging.info("invalid date format: %s" % date_string)
				# 日付の範囲チェックしつつ型変換
				try:
					relevant_date = datetime.date(year, month,day)
				except ValueError:
					year = 1999
					month = 1
					day = 1
					relevant_date = datetime.date(year, month,day)
					logging.info("invalid date range: %s" % date_string)
			else:
				#dateパラメータが無ければ当日
				relevant_date = Relevant_date.get_by_key_name("relevant_date").date
				logging.debug("relevant date fetched: %s" % relevant_date.strftime("%Y-%m-%d"))
			return relevant_date
		
		#基準日の取得
		relevant_date = get_date(self.request.get("date"))
		logging.debug("relevant date: %s" % relevant_date.strftime("%Y-%m-%d"))
		#text/plain指定
		self.response.headers["Content-Type"] = "text/plain;charset=UTF-8"
		#CSVヘッダを作成
		self.response.out.write(u'"日付","RANK","カテゴリ","タイトル","動画URL","サムネイルURL"' + "\n")
		#CSVデータの生成
		#基準日分のデータを取得
		rankings = Ranking.gql("WHERE date = :date ORDER BY rank, category_number", date=relevant_date)
		for ranking in rankings:
			#CSVに編集
			line = '"' +	\
				ranking.date.strftime("%Y-%m-%d") + '","' +	\
				str(ranking.rank) + '","' + 				\
				ranking.category_name + '","' +	 			\
				ranking.title + '","' +	 					\
				ranking.movie_url + '","' +					\
				ranking.sumnail_url	+ '"' + "\n"
			#responseとして出力
			self.response.out.write(line)


class JapanTZ(datetime.tzinfo):
    def tzname(self, dt):
        return "JST"
    def utcoffset(self, dt):
        return datetime.timedelta(hours=9)
    def dst(self, dt):
        return datetime.timedelta(0)


class Time(webapp.RequestHandler):
	def get(self):
		self.response.out.write(datetime.datetime.now(JapanTZ()).strftime("%Y-%m-%d %H:%M:%S"))


logging.getLogger().setLevel(logging.DEBUG)
application = webapp.WSGIApplication([("/report",Report),("/time",Time),("/.*",CSV)],debug=True)

		
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

