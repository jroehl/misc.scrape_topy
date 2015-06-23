#!/usr/bin/env python3

import re
import csv
import sys
import os
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def scrape(arg):

    # return arg
    # lists = scrape()
    # write_to_CSV("scraped", lists)
    if not arg.startswith('http://'):
        arg = "http://{0}" .format(arg)

    browser = webdriver.Firefox()
    browser.implicitly_wait(2.5)
    browser.get("{0}" .format(arg))
    # browser.get('http://topsy.com/s?q=from%3ALOTR&mintime=1388617248')
    count = 0
    set = {  # 10
           "tweet_id": [],
             # 11
           "twitter_id": [],
             # 2
           "created_at": [],
             # 4
           "language": [],
             # 9
           "truncated": [],
             # 7
           "source": [],
             # 1
           "coordinates": [],
             # 5
           "reply_user_id": [],
             # 6
           "retweet_count": [],
             # 3
           "favorite_count": [],
             # 8
           "text": [],
           "count": count
           }

    while count % 10 == 0:

        set = scrape_topsy(browser, set)
        count = set["count"]
        try:
            next_btn = browser.find_element_by_xpath("//*[@id='module-pager']/div/ul/li[12]/a")
        except Exception as e:
            log("Not a topsy URL specified:\n{0}" .format(e))
            sys.exit(0)
        next_btn.click()

    header = ["Coordinates",
              "CreatedAt",
              "FavoriteCount",
              "Language",
              "RepUserID",
              "RetweetCount",
              "Source",
              "Text",
              "Truncated",
              "TweetID",
              "TwitterID"
              ]

    write_list = []
    write_list.append(header)

    browser.get("http://gettwitterid.com/")
    name = set["twitter_id"][0]
    search_bar = browser.find_element_by_xpath("//*[@id='search_bar']")
    search_bar.send_keys(name)
    search_bar.send_keys(Keys.RETURN)

    result = browser.find_element_by_xpath("/html/body/div/div[1]/table/tbody/tr[1]/td[2]/p").text

    set["twitter_id"] = [result for item in set["twitter_id"]]

    del set["count"]
    for count in range(len(set["tweet_id"])):
        write_list.append([set[key][count] for key in sorted(set)])

    write_to_CSV(name, write_list)

    browser.quit()

    log("{0} tweets scraped and saved to {1}.csv.." .format(count, name))


def scrape_topsy(browser, set):

    html_source = browser.page_source

    soup = BeautifulSoup(html_source)
    results = soup.find_all("div", class_="media-body")

    count = 0
    for result in results:
        count += 1

        text = result.find("div")
        text = tweet_regex(str(text))

        twitter_id = result.find("a")
        twitter_id = re.search('(?<=twitter.com/).*?(")', str(twitter_id)).group()
        twitter_id = twitter_id.replace("\"", "")

        muted = result.find_all("a", class_="muted")

        rep_to = re.search('(?<=status/)\d+', str(muted)).group()

        tweet_id = re.search('(?<=status/)\d+', str(muted)).group()

        created_at = re.search('(?<=timestamp=")\d+', str(muted)).group()
        created_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(created_at)))

        counts = browse_twitter(browser, result, count)

        set["tweet_id"].append(tweet_id)
        set["twitter_id"].append(twitter_id)
        set["created_at"].append(created_at)
        set["language"].append(None)
        set["truncated"].append(False)
        set["source"].append(None)
        set["coordinates"].append(None)
        set["reply_user_id"].append(rep_to)
        set["retweet_count"].append(counts[0])
        set["favorite_count"].append(counts[1])
        set["text"].append(text)
        set["count"] = count

    return set


def page_has_loaded(browser):
        try:
            time.sleep(0.5)
            browser.find_element_by_xpath("//*[@id='doc']")
            return True
        except:
            return False


def browse_twitter(browser, result, count):

    browser.find_element_by_tag_name('a')

    main_window = browser.current_window_handle
    if count >= 6:
        count += 1
    tweet = browser.find_element_by_xpath("//*[@id='results']/div[{0}]/div/div/ul/li[1]/small/a/span[2]" .format(count))

    action = ActionChains(browser)
    action.key_down(Keys.COMMAND)
    action.click(tweet)
    action.key_up(Keys.COMMAND)
    action.perform()

    browser.find_element_by_tag_name('body').send_keys(Keys.CONTROL + Keys.TAB)

    # Try
    # WebDriverWait(browser, 10).until(
    #     EC.presence_of_element_located((By.XPATH, "//*[@id='doc']"))
    # )

    for count in range(3):
        if not page_has_loaded(browser):
            if count == 2:
                browser.find_element_by_tag_name('body').send_keys(Keys.COMMAND + 'w')
                browser.switch_to_window(main_window)
                return [0, 0]
            browser.refresh()

    html_source = browser.page_source
    soup = BeautifulSoup(html_source)
    retweet_count = soup.find_all(class_="request-retweeted-popup")
    retweet_count = re.search('(?<=<strong>)\d+', str(retweet_count)).group()
    favorite_count = soup.find_all(class_="request-favorited-popup")
    favorite_count = re.search('(?<=<strong>)\d+', str(favorite_count)).group()

    browser.find_element_by_tag_name('body').send_keys(Keys.COMMAND + 'w')

    browser.switch_to_window(main_window)

    return [retweet_count, favorite_count]


def tweet_regex(string):
    tweet = re.sub('<div>', '', string)
    tweet = re.sub('</div>', '', tweet)
    tweet = re.sub('<a data-hashtag=', ' ', tweet)
    tweet = re.sub('<a data-username=', ' ', tweet)
    tweet = re.sub('<a href=', ' ', tweet)
    tweet = re.sub('href=.*?(>)', '', tweet)
    tweet = re.sub('</a>', ' ', tweet)
    tweet = re.sub('>pic.twitter.com.*', ' ', tweet)
    tweet = re.sub('"', '', tweet)

    return tweet


def write_to_CSV(name, lists):
    """Write the tweets to a CSV file."""
    # create directory (if not exists) temp_csv on desktop
    desktop_path = "{0}/Desktop" .format(os.getcwd().replace("/scripts", ""))
    mk_dir("temp_csv")
    filename = '{0}/temp_csv/{1}.csv' .format(desktop_path, name)

    try:
        # write the csv
        with open('{0}' .format(filename), 'a') as f:
            writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writerows(lists)
    except Exception as e:
        log("{0} : Problem writing to file" .format(e))


def log(output):
    with open("{0}/temp.log" .format(os.getcwd()), "a") as log:
        log.write(output)


def mk_dir(dirname):
    """Try to create directory, pass if it fails."""
    try:
        os.makedirs('{0}/Desktop/{1}' .format(os.getcwd().replace("/scripts", ""), dirname))
    except:
        pass


if __name__ == "__main__":
    try:
        scrape(sys.argv[1])
    except Exception as e:
        log("Error starting script:\n{0}" .format(e))