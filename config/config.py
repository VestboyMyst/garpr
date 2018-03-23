from ConfigParser import ConfigParser

import logging

DEFAULT_CONFIG_PATH = './config/config.ini'

class Config(object):
    def __init__(self, config_file_path=DEFAULT_CONFIG_PATH):
        self.config = ConfigParser()
        self.config.read(config_file_path)

    def get_mongo_url(self):
        return 'mongodb://%s:%s@%s/%s' % (
                self.get_db_user(),
                self.get_db_password(),
                self.get_db_host(),
                self.get_auth_db_name())

    def get_environment_name(self):
        return self.config.get('environment', 'name')

    def get_environment_host(self):
        return self.config.get('environment', 'host')

    def get_environment_web_port(self):
        return self.config.get('environment', 'web_port')

    def get_environment_api_port(self):
        return self.config.get('environment', 'api_port')

    def get_environment_http_redirect_port(self):
        return self.config.get('environment', 'http_redirect_port')

    def get_environment_backups_directory(self):
        return self.config.get('environment', 'backups_directory')

    def get_ssl_key_path(self):
        return self.config.get('ssl', 'key_path')

    def get_ssl_cert_path(self):
        return self.config.get('ssl', 'cert_path')

    def get_db_host(self):
        return self.config.get('database', 'host')

    def get_auth_db_name(self):
        return self.config.get('database', 'auth_db')

    def get_db_name(self):
        return self.config.get('database', 'db')

    def get_db_user(self):
        return self.config.get('database', 'user')

    def get_db_password(self):
        return self.config.get('database', 'password')

    def get_challonge_api_key(self):
        return self.config.get('challonge', 'api_key')

    def get_fb_app_id(self):
        return self.config.get('facebook', 'app_id')

    def get_fb_app_token(self):
        return self.config.get('facebook', 'app_token')

    def get_loaderio_token(self):
        return self.config.get('loaderio', 'token')

    def get_dropbox_app_key(self):
        return self.config.get('dropbox', 'app_key')

    def get_dropbox_app_secret(self):
        return self.config.get('dropbox', 'app_secret')

    def get_dropbox_access_token(self):
        return self.config.get('dropbox', 'access_token')

    def get_logging_level(self):
        lvl = self.config.get('logging', 'level')

        # set default level to WARNING if invalid level
        if lvl not in ('DEBUG', 'WARNING', 'INFO', 'CRITICAL', 'ERROR'):
            print lvl + ' is not a valid level. Please use DEBUG, INFO, WARNING, ERROR, or CRITICAL'
            logging.warning(lvl + ' is not a valid level. Please use DEBUG, INFO, WARNING, ERROR, or CRITICAL')
            lvl = 'WARNING'

        if lvl is 'DEBUG':
            lvl = logging.DEBUG
        elif lvl is 'INFO':
            lvl = logging.INFO
        elif lvl is 'WARNING':
            lvl = logging.WARNING
        elif lvl is 'ERROR':
            lvl = logging.ERROR
        elif lvl is 'CRITICAL':
            lvl = logging.CRITICAL

        return lvl