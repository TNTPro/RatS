import csv
import datetime
import os
import re
import sys
import time

from selenium.common.exceptions import TimeoutException

from RatS.base.base_ratings_parser import Parser
from RatS.movielens.movielens_site import Movielens
from RatS.utils import file_impex

TIMESTAMP = datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')


class MovielensRatingsParser(Parser):
    def __init__(self, args):
        super(MovielensRatingsParser, self).__init__(Movielens(args), args)
        self.exports_folder = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'RatS', 'exports'))
        self.csv_filename = '%s_%s.csv' % (TIMESTAMP, 'Movielens')

    def _parse_ratings(self):
        self._download_ratings_csv()
        self._rename_csv_file()
        self.movies = self._parse_movies_from_csv(os.path.join(self.exports_folder, self.csv_filename))

    def _download_ratings_csv(self):
        sys.stdout.write('\r===== %s: Retrieving ratings CSV file' % self.site.site_name)
        sys.stdout.flush()
        self.site.browser.set_page_load_timeout(5)
        time.sleep(1)
        try:
            self.site.browser.get('https://movielens.org/api/users/me/movielens-ratings.csv')
        except TimeoutException:
            time.sleep(1)

    def _rename_csv_file(self):
        filepath = os.path.join(self.exports_folder, 'movielens-ratings.csv')
        file_impex.wait_for_file_to_exist(filepath)

        try:
            os.rename(filepath, os.path.join(self.exports_folder, self.csv_filename))
            sys.stdout.write('\r===== %s: CSV downloaded to %s/%s\r\n' %
                             (self.site.site_name, self.exports_folder, self.csv_filename))
            sys.stdout.flush()
        except FileNotFoundError:
            sys.stdout.write('\r===== %s: Could not retrieve ratings CSV\r\n' % self.site.site_name)
            sys.stdout.flush()

    def _parse_movies_from_csv(self, filepath):
        sys.stdout.write('===== getting movies from CSV\r\n')
        sys.stdout.flush()
        file_impex.wait_for_file_to_exist(filepath)
        with open(filepath, newline='') as input_file:
            reader = csv.reader(input_file, delimiter=',')
            next(reader, None)  # ignore csv header
            return [self._convert_csv_row_to_movie(row) for row in reader]

    def _convert_csv_row_to_movie(self, row):
        movie = dict()

        if self.args and self.args.verbose and self.args.verbose >= 1:
            sys.stdout.write('\r===== %s: reading movie from CSV: \r\n' % self.site.site_name)
            for r in row:
                sys.stdout.write(r + '\r\n')
            sys.stdout.flush()

        find_year = re.findall(r'(\(\d{4}\))', row[5])
        if find_year:
            year = find_year[-1]
            movie['year'] = int(re.findall(r'\((\d{4})\)', row[5])[-1])
        else:  # no movie year in CSV
            year = '()'
            movie['year'] = 0
        movie['title'] = row[5].replace(year, '').strip()

        movie[self.site.site_name.lower()] = dict()
        movie[self.site.site_name.lower()]['id'] = row[0]
        movie[self.site.site_name.lower()]['url'] = 'https://movielens.org/movies/' + row[0]
        movie[self.site.site_name.lower()]['my_rating'] = int(float(row[3]) * 2)

        movie['imdb'] = dict()
        movie['imdb']['id'] = row[1]
        if 'tt' not in movie['imdb']['id']:
            movie['imdb']['id'] = 'tt' + row[1]
        movie['imdb']['url'] = 'http://www.imdb.com/title/' + movie['imdb']['id']

        movie['tmdb'] = dict()
        movie['tmdb']['id'] = row[2]
        movie['tmdb']['url'] = 'https://www.themoviedb.org/movie/' + movie['tmdb']['id']

        return movie