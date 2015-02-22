__author__ = 'ndenev@gmail.com'

import json
import requests
import cerberus
from urllib import urlencode
from functools import partial

VERSION = '0.0.1'


class SeyrenException(Exception):
    pass


class SeyrenAlertException(SeyrenException):
    pass


class SeyrenCheckException(SeyrenException):
    pass


class SeyrenDataValidationError(SeyrenException):
    pass


def _setter(obj, value, key):
    if obj._validator({key: value}, {key: obj._validation_schema[key]}):
       obj._data[key] = value 
    else:
       raise SeyrenDataValidationError("Failed to validate value: {}".format(obj._validator.errors))

def _getter(obj, key):
    return obj._data.get(key, None)

def _deleter(obj, key):
    obj._data[key] = None

def _gen_props(obj, params):
    if not obj._validator(params, obj._validation_schema):
        raise SeyrenDataValidationError("Failed to validate data: {}".format(obj._validator.errors))
    for key in obj._validation_schema.keys():
        obj._data[key] = params.get(key, None)
        setattr(obj.__class__, key, property(partial(_getter, key=key), partial(_setter, key=key), partial(_deleter, key=key)))


class SeyrenSubscription(object):
    _validator = cerberus.Validator()
    _validation_schema = {'target': {'type': 'string'},
                          'type': {'type': 'string'},
                          'ignoreWarn': {'type': 'boolean'},
                          'ignoreError': {'type': 'boolean'},
                          'ignoreOk': {'type': 'boolean'},
                          'notifyOnWarn': {'type': 'boolean'},
                          'notifyOnError': {'type': 'boolean'},
                          'notifyOnOk': {'type': 'boolean'},
                          'fromTime': {'type': 'string', 'regex': '(2[0-4]|[0-1][0-9])[0-5][0-9]'},
                          'toTime': {'type': 'string', 'regex': '(2[0-4]|[0-1][0-9])[0-5][0-9]'},
                          'su': {'type': 'boolean'},
                          'mo': {'type': 'boolean'},
                          'tu': {'type': 'boolean'},
                          'we': {'type': 'boolean'},
                          'th': {'type': 'boolean'},
                          'fr': {'type': 'boolean'},
                          'sa': {'type': 'boolean'},
                          'enabled': {'type': 'boolean'}}

    def __init__(self, subscription_params):
        self._data = {}
        _gen_props(self, subscription_params)


class SeyrenCheck(object):
    _validator = cerberus.Validator()
    _validation_schema = {'checkId': {'type': 'string', 'regex': '[0-9a-f]+' },
                          'fromType': {'type': 'string' },
                          'toType': {'type': 'string' },
                          'target': {'type': 'string' },
                          'timestamp': {'type': 'integer' },
                          'value': {'type': 'number' },
                          'warn': {'type': 'string' },
                          'error': {'type': 'string' },
                          'targetHash': {'type': 'string' },
                          'id': {'type': 'string', 'regex': '[0-9a-f]+' }}

    def __init__(self, check_params):
        self._data = {}
        _gen_props(self, check_params)


    def get_alerts(self):
        ''' Get alerts for this check '''
        pass

    def delete_alerts(self, before):
        ''' Delete alerts for this check before the specified date
        :param before: the date before to delete alerts
        :param type: datetime
        :returns: Nothing on success, or throws exception
        :rtype: None
        :raises: SeyrenAlertException
        '''
        pass

    def create(self, check):
        '''
        Parameter	Required	Description	                Type
        name	        true	        Name of the check	        String
        description	false	        Description of the check	String
        target	        true	        Name of the metric in graphite	String
        warn	        true	        Warn level	                String
        error	        true	        Error level	                String
        enabled	        true	        Enable/Disable value	        boolean
        live	        false	        Live value (pickle protocol)	boolean
        from	        false	        Specifies the beginning	        String
        until	        false	        Specifies the end	        String
        '''
        pass

    def update(self):
        pass

    def delete(self):
        pass

    def create_subscription(self):
        pass

    def update_subscription(self):
        pass

    def delete_subscription(self):
        pass

    def test_subscription(self, subscription):
        pass
    

class SeyrenAlert(object):
    _alert_fields = ['checkId',
                     'fromType',
                     'toType',
                     'target',
                     'timestamp',
                     'value',
                     'warn',
                     'error',
                     'targetHash',
                     'id']

    def __init__(self, alert):
        for field in self._alert_fields:
            if field not in alert:
                raise SeyrenAlertException('Missing required field: {}'.format(field))
            setattr(self, field, alert[field])

    def __repr__(self):
        return "SeyrenAlert(id: {}, checkId: {}, target: {}, change: {}->{})".format(self.id, self.checkId, self.target, self.fromType, self.toType)

    def __str__(self):
        return self.__repr__()


class SeyrenClient(object):
    def __init__(self, url="http://localhost:8081", auth=None):
        ''' Instantiate new Seyren API client
        :param url: URL of the Seyren Web UI (without /api)
        :type url: string
        :param auth: Authentication method passed to Requests library
        :param type: (user,pass) tuple or other supported authentication.
        :returns: Seyren API client object
        :rtype: SeyrenClient
        '''

        self._url = url
        self._session = requests.Session()
        self._session.headers = headers = {'User-Agent': 'PySeyrenClient-{}'.format(VERSION)}
        if auth is not None:
            self._session.auth = auth

    def _api_call(self, method, url, params=None):
        ''' Make a call to the API
        :param method: Requests recognized HTTP method.
        :type method: string
        :param url: URL to call
        :type url: string
        :param params: Parameters to pass with the HTTP request.
        :tyep params: dict
        '''

        req = requests.Request(url=url, method=method.upper(), params=params, headers=self._session.headers)
        preq = self._session.prepare_request(req)
        resp = self._session.send(preq)
        resp.raise_for_status()
        return resp.json()

    def get_metric_count(self, path):
        ''' Get the number of metrics that match the given path
        :param path: metric path e.g.: host.path.metric.xxx
        :type path: string
        :returns: number of matching metrics
        :rtype: int
        '''
        query_url = '{}/api/metrics/{}/total'.format(self._url, path)
        response = self._api_call('GET', query_url)
        return int(response[path])

    def get_alerts(self, start=0, items=20):
        alerts = []
        total = 1
        while len(alerts) < total:
            params = {'start': start, 'items': items}
            alert_data = self._api_call('GET', self._url + '/api/alerts', params=urlencode(params))
            total = alert_data['total']
            items = alert_data['items']
            start = alert_data['start'] + items
            alerts.extend([SeyrenAlert(alert) for alert in alert_data['values']])
        return alerts

    def get_checks(self, **kwargs):
        ''' Get all configured checks
        Optional kwargs:
        state
        enabled
        name
        fields
        regexes
        '''
        pass

    def get_check(self, checkId):
        pass


    def get_chart_for_target(self, target):
        pass

