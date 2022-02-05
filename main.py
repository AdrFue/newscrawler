import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

import sqlite3


def clickPopupFrame():
  time.sleep(1)

  # Check if it even appears
  if len(driver.find_elements(By.ID, "sp_message_container_545340")) != 0:   # If it does, click it  
    driver.switch_to.frame("sp_message_iframe_545340")
    popupBtn = driver.find_element(By.XPATH, "//button[text()='EINVERSTANDEN']")
    popupBtn.click()
    driver.switch_to.default_content()


def definePeriod():
  time.sleep(1)
  filter = driver.find_element(By.CLASS_NAME, "filterListe")
  period = filter.find_element(By.CLASS_NAME, "sub")

  ActionChains(driver).move_to_element(period).perform()
  time.sleep(1)

  from_input = driver.find_element(By.ID, "from")
  from_input.send_keys("00.00.0000")
  
  to_input = driver.find_element(By.ID, "to")
  to_input.send_keys("29.01.2022")

  ok_button = period.find_element(By.CLASS_NAME, "SubmitBtn")
  ok_button.click()

  time.sleep(1)

def get_id(cur):
  sql_id = "SELECT fa_id FROM faz_articles ORDER BY fa_id DESC LIMIT 1;";

  cur.execute(sql_id)
  rows = cur.fetchall()
  return rows[0][0]


# chrome driver
co = Options()  
co.headless = False
co.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = webdriver.Chrome('res/chromedriver', options=co)
print("\n")
driver.get("https://www.faz.net/faz-live")
driver.maximize_window()
time.sleep(1)
clickPopupFrame()

# define Period
definePeriod()
logo = driver.find_element(By.CLASS_NAME, "gh-CenterNav_Logo")
ActionChains(driver).move_to_element(logo).perform()

# SQL Connection
conn = sqlite3.connect("D:\\Dokumente\\SQLite\\newscrawler.db")
cur = conn.cursor()

# crawling
while(True): # immer weiter nach hinten

  # get articles
  ticker = driver.find_element(By.ID, "FAZContentLeftInner")
  tickerLinks = ticker.find_elements(By.TAG_NAME, "a")

  links = [None] * len(tickerLinks)
  for i in range(len(tickerLinks)):
    links[i] = tickerLinks[i].get_attribute("href")
  
  # open new tab
  driver.execute_script('''window.open("", "_blank");''')
  driver.switch_to.window(driver.window_handles[1])
  time.sleep(1)

  # going into articles
  for i in range(0, len(links), 2):
    link = links[i]

    driver.get(link)
    clickPopupFrame()

    print("Looking at " + link)

    ressorts = []
    if "agenturmeldungen" in link:
        ressorts.append("agenturmeldungen")
    else:
        linkParts = link[28:link.rfind("/")]
        ressorts = linkParts.split("/")

    # Header
    emphasis = ""
    if len(driver.find_elements(By.CLASS_NAME, "atc-HeadlineEmphasisText")) != 0:
        emphasis = driver.find_element(By.CLASS_NAME, "atc-HeadlineEmphasisText").text
    
    if len(driver.find_elements(By.CLASS_NAME, "atc-HeadlineText")) <= 0:
      continue

    headline = driver.find_element(By.CLASS_NAME, "atc-HeadlineText").text

    # Date and Time
    timestamp = driver.find_element(By.CLASS_NAME, "atc-MetaTime").get_attribute("datetime")
    date_str = timestamp[0:10]
    time_str = timestamp[11:19]

    # readtime
    rawReadTime = driver.find_element(By.CLASS_NAME, "atc-ReadTime_Text").text
    readTime = int(rawReadTime[0:len(rawReadTime) - 5])

    # Author and Place
    author = ""
    place = ""

    if len(driver.find_elements(By.CLASS_NAME, "atc-MetaAuthorLink")) != 0:
      authorAndPlace = driver.find_element(By.CLASS_NAME, "atc-MetaAuthorLink").text
      splitter = authorAndPlace.find(",")
      # Only Author or with plade
      if splitter > 0:
        author = authorAndPlace[0:splitter]
        place = authorAndPlace[splitter+1:len(authorAndPlace)]
      else:
        author = authorAndPlace

    # Text
    text = ""
    pages = 1

    if len(driver.find_elements(By.CLASS_NAME, "atc-Intro")) != 0:
      text = driver.find_element(By.CLASS_NAME, "atc-Intro").text

    # multiple pages
    if len(driver.find_elements(By.CLASS_NAME, "nvg-Paginator_Item-page-number")) != 0:
      pages = len(driver.find_elements(By.CLASS_NAME, "nvg-Paginator_Item-page-number"))

    for j in range(1, pages):
      # multiple paragraphs
      if len(driver.find_elements(By.CLASS_NAME, "atc-TextParagraph")) != 0:
        paras = driver.find_elements(By.CLASS_NAME, "atc-TextParagraph")
        paraSize = len(paras)
        for para in paras:
          text += "\n" + para.text

        if j == pages:
          break

        if len(driver.find_elements(By.CLASS_NAME, "nvg-Paginator_Item-page-number")) != 0:
          time.sleep(1)
          driver.find_elements(By.CLASS_NAME, "nvg-Paginator_Item-page-number")[j].click()

    # Source
    if len(driver.find_elements(By.CLASS_NAME, "atc-Footer_Quelle")) != 0:
      rawSource = driver.find_element(By.CLASS_NAME, "atc-Footer_Quelle").text
      if len(rawSource) > 8:
        source = rawSource[8:len(rawSource)]

    # Comments
    comments = False
    if len(driver.find_elements(By.CLASS_NAME, "atc-ContainerSocialMedia")) != 0:
      pageFnc = driver.find_element(By.CLASS_NAME, "atc-ContainerSocialMedia")
      if len(pageFnc.find_elements(By.CLASS_NAME, "ico-Base_Comment")) != 0:
        comments = True

    # Themes
    themes = []
    if len(driver.find_elements(By.CLASS_NAME, "lst-LinksTopics_TopicsListItem")) != 0:
      rawThemes = driver.find_elements(By.CLASS_NAME, "lst-LinksTopics_TopicsListItem")
      for i in range(len(rawThemes)-1):
        themes.append(rawThemes[i].text)

    time.sleep(1)

    # SQL Article
    sqlArticle = """INSERT INTO faz_articles(
      fa_headline, fa_emphasis, fa_date, fa_time, fa_author, 
      fa_place, fa_readTime, fa_pages, fa_text, fa_source, 
      fa_comments, fa_link, fa_ts)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    dataArticle = [(headline, emphasis, date_str, time_str, 
      author, place, readTime, pages, text, 
      source, comments, link, datetime.now())]
    cur.executemany(sqlArticle, dataArticle)  
    conn.commit()

    id = get_id(cur)

    # SQL Ressorts
    sqlRessorts = """INSERT INTO faz_ressorts(
      fr_fa_id, fr_ressort, fr_depth, fr_ts
      ) VALUES(?, ?, ?, ?)"""
    
    for i in range(len(ressorts)):
      dataRessorts = [(id, ressorts[i], i, datetime.now())]
      cur.executemany(sqlRessorts, dataRessorts)
    conn.commit()

    # SQL Themes
    sqlThemes = """INSERT INTO faz_themes(
      ft_fa_id, ft_theme, ft_ts
      ) VALUES(?, ?, ?)"""
    
    for i in range(len(themes)):
      dataThemes = [(id, themes[i], datetime.now())]
      cur.executemany(sqlThemes, dataThemes)
    conn.commit()

    time.sleep(1)

  # close open tab
  driver.execute_script('''window.close();''')
  driver.switch_to.window(driver.window_handles[0])

  driver.find_element(By.CLASS_NAME, "Next").click()
  time.sleep(1)


# closing connection and driver
print("\n\n")
conn.close()
driver.close()