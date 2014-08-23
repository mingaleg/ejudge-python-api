__author__ = 'shhdup'

LOGIN = 'user'
PASSWORD = 'password'
MASTER_URL = 'https://ejudge.lksh.ru/cgi-bin/new-master'

MASTER_LOGIN = MASTER_URL + '?contest_id={contest_id}&locale_id=0&login={login}&password={password}&role=6'

from urllib import request
import re
from datetime import datetime
from urllib.request import quote


class EjudgeException(Exception):
    pass


class Contest:
    def __init__(self, contest_id, login=LOGIN, password=PASSWORD):
        self.contest_id = int(contest_id)
        self.login = login
        self.password = password
        self.SID = ''
        self.EJSID = ''
        self.update_sid()

    def update_sid(self):
        url = MASTER_LOGIN.format(contest_id=self.contest_id, login=self.login, password=self.password)
        req = request.urlopen(url)
        if 'sid' in req.url.lower():
            self.SID = req.url[req.url.lower().find('sid=')+4:][:16]
            print(dir(req))
            self.EJSID = req.cookies['EJSID']
            return (self.SID, self.EJSID)

        out = req.read().decode('utf-8')
        fails_titles = (
            ('<title>Invalid session</title>', 'Invalid session'),
            ('<title>Login page</title>', 'Login page'),
            ('<title>Permission denied</title>', 'Permission denied'),
            ('<title>Invalid parameter</title>', 'Invalid parameter'),
        )

        for title, reason in fails_titles:
            if title in out:
                raise EjudgeException(reason)

        out = out.split('\n')
        sidline = filter((lambda x: x.startswith('var SID=')), out).__iter__().__next__()
        self.SID = sidline[len("var SID='"):-2]
        self.EJSID = req.cookies['EJSID']
        return (self.SID, self.EJSID)

    def raw_request(self, **kwargs):
        url = MASTER_URL + '?'
        for key, val in kwargs.items():
            url += '{key}={val}&'.format(key=key, val=quote(str(val)))

        def urlopen():
            out = request.urlopen('{url}SID={SID}'.format(url=url,SID=self.SID), cookies={'EJSID': self.EJSID})
            print(out.url)
            input()
            out = out.read()
            out = out.decode('utf-8')
            return out

        out = urlopen()
        fails_titles = (
            ('<title>Invalid session</title>', 'Invalid session'),
            ('<title>Login page</title>', 'Login page'),
            ('<title>Permission denied</title>', 'Permission denied'),
            ('<title>Invalid parameter</title>', 'Invalid parameter'),
        )

        for title, reason in fails_titles:
            if title in out:
                self.update_sid()
                out = urlopen()
                break

        for title, reason in fails_titles:
            if title in out:
                raise EjudgeException(reason)

        return out

    def Start(self):
        self.raw_request(action=42)

    def Stop(self):
        self.raw_request(action=43)

    def Continue(self):
        self.raw_request(action=44)

    def Reset(self):
        self.raw_request(action=115)

    def UpdatePublicStandings(self):
        self.raw_request(action=114)

    def SuspendClients(self):
        self.raw_request(action=49)

    def ResumeClients(self):
        self.raw_request(action=50)

    def SuspendTesting(self):
        self.raw_request(action=51)

    def ResumeTesting(self):
        self.raw_request(action=52)

    def StopUpsolving(self):
        self.raw_request(action=185)

    def StartUpsolving(self,
                       freeze_standings=True, view_source=True, view_protocol=True,
                       full_protocol=False, disable_clars=True):
        foo = {}
        if freeze_standings:
            foo['freeze_standings'] = 'on'
        if view_source:
            foo['view_source'] = 'on'
        if view_protocol:
            foo['view_protocol'] = 'on'
        if full_protocol:
            foo['full_protocol'] = 'on'
        if disable_clars:
            foo['disable_clars'] = 'on'
        self.raw_request(action=186, **foo)

    def ReloadConfigFiles(self):
        self.raw_request(action=62)

    def ChangeViewSourcePolicy(self, mode):
        if mode not in ('Yes', 'No', 'Default'):
            raise EjudgeException('mode should be "Yes", "No" or "Default", not {mode}'.format(mode=mode))
        mode = {'Yes': 1, 'No': -1, 'Default': 0}[mode]
        self.raw_request(action=248, param=mode)

    def ChangeViewReportsPolicy(self, mode):
        if mode not in ('Yes', 'No', 'Default'):
            raise EjudgeException('mode should be "Yes", "No" or "Default", not {mode}'.format(mode=mode))
        mode = {'Yes': 1, 'No': -1, 'Default': 0}[mode]
        self.raw_request(action=249, param=mode)

    def ChangeViewReportsPolicy(self, mode):
        if mode not in ('Yes', 'No'):
            raise EjudgeException('mode should be "Yes" or "No", not {mode}'.format(mode=mode))
        mode = {'Yes': 1, 'No': 0}[mode]
        self.raw_request(action=251, param=mode)

    def upload_raw_run(self, run_id):
        return self.raw_request(run_id=run_id, action=91)

    def Run(self, run_id):
        return Run(self, run_id)

    def Message(self, msg_subj, msg_text, msg_dest_login='ALL', msg_dest_id=None):
        if msg_dest_id:
            return self.raw_request(msg_text=msg_text, msg_subj=msg_subj, msg_dest_id=msg_dest_id, action=63)
        else:
            return self.raw_request(msg_text=msg_text, msg_subj=msg_subj, msg_dest_login=msg_dest_login, action=63)

    def DownloadRuns(self,
                     selection='all', file_pattern_run=True, file_pattern_uid=False,
                     file_pattern_login=False, file_pattern_name=False, file_pattern_prob=False,
                     file_pattern_lang=False, file_pattern_suffix=True):
        #TODO: Downloading with byte mode(!)
        pass


class Run:
    def __init__(self, contest, run_id, cache=False):
        self.contest = contest
        self.run_id = run_id
        self.cache = cache
        self._raw_source_page = None
        self._source = None

        for prop in self.common_properties:
            setattr(self, '_'+prop, None)
            setattr(Run, prop, property(self.property_fabric(prop), self._readonly))

    @classmethod
    def property_fabric(cls, prop):
        def get(self):
            if not self.cache and self.__getattribute__('_' + prop) is None:
                self.parse_source_page()
            return self.__getattribute__('_' + prop)
        return get

    def _readonly(self):
        raise "Read Only"

    common_properties = (
        'time', 'contest_time', 'originator_ip', 'user_id', 'user_login', 'user_name',
        'problem_name', 'problem_longname', 'language', 'status', 'tests_passed',
        'marked', 'imported', 'hidden', 'saved', 'read_only', 'locale_id', 'size',
        'hash', 'pages_printed',
    )

    def raw_request(self, **kwargs):
        return self.contest.raw_request(run_id=self.run_id, **kwargs)

    @property
    def raw_source_page(self):
        if self._raw_source_page is None:
            self._raw_source_page = self.raw_request(action=36)
        return self._raw_source_page

    @property
    def source(self):
        if self._source is None:
            self._source = self.raw_request(action=91)
        return self._source

    def Reject(self, msg_text=''):
        self.raw_request(action=235, msg_text=msg_text)

    def OK(self, msg_text=None):
        if msg_text is None:
            self.raw_request(action=234)
        else:
            self.raw_request(action=232, msg_text=msg_text)

    def Ignore(self, msg_text=None):
        if msg_text is None:
            self.raw_request(action=233)
        else:
            self.raw_request(action=228, msg_text=msg_text)

    def Comment(self, msg_text):
        self.raw_request(action=64, msg_text=msg_text)

    def ChangeStatus(self, status):
        self.raw_request(action=67, status=status)

    def Rejudge(self):
        self.ChangeStatus(99)

    def FullRejudge(self):
        self.ChangeStatus(95)

    def Disqualify(self):
        self.ChangeStatus(10)

    def CheckFailed(self):
        self.ChangeStatus(6)

    def PendingCheck(self):
        self.ChangeStatus(11)

    def PartialSolution(self):
        self.ChangeStatus(7)

    def Accepted(self):
        self.ChangeStatus(8)

    def PendingReview(self):
        self.ChangeStatus(16)

    def CompilationError(self):
        self.ChangeStatus(1)

    def RunTimeError(self):
        self.ChangeStatus(2)

    def TimeLimitExceeded(self):
        self.ChangeStatus(3)

    def WallTimeLimitExceeded(self):
        self.ChangeStatus(15)

    def PresentationError(self):
        self.ChangeStatus(4)

    def WrongAnswer(self):
        self.ChangeStatus(5)

    def MemoryLimitExceeded(self):
        self.ChangeStatus(12)

    def SecurityViolation(self):
        self.ChangeStatus(13)

    def CodingStyleViolation(self):
        self.ChangeStatus(14)

    def parse_source_page(self):
        raw = self.raw_source_page

        pattern = '<tr><td.*?>{sprop}</td><td.*?>(<a.*?>)?(?P<val>.*?)(</a>)?</td></tr>'
        for prop, sprop in (
            ('_time', 'Submission time:'),
            ('_contest_time', 'Contest time:'),
            ('_originator_ip', 'Originator IP:'),
            ('_user_id', 'User ID:'),
            ('_user_login', 'User login:'),
            ('_user_name', 'User name:'),
            ('_problem_longname', 'Problem:'),
            ('_language', 'Language:'),
            ('_status', 'Status:'),
            ('_tests_passed', 'Tests passed:'),
            ('_marked', 'Marked\?:'),
            ('_imported', 'Imported\?:'),
            ('_hidden', 'Hidden\?:'),
            ('_saved', 'Saved\?:'),
            ('_read_only', 'Read-only\?:'),
            ('_locale_id', 'Locale ID:'),
            ('_size', 'Size:'),
            ('_hash', 'Hash value:'),
            ('_pages_printed', 'Pages printed:'),
        ):
            try:
                cl = re.finditer(pattern.format(sprop=sprop), raw).__iter__().__next__().groupdict()['val']
                self.__setattr__(prop, cl)
            except:
                self.__setattr__(prop, None)

        if self._status is None:
            raise EjudgeException('Bad run')

        try:
            self._time = datetime.strptime(':'.join(self._time.split(':')[:-1]), '%Y/%m/%d %H:%M:%S')
        except:
            pass


def get_run(name):
    name = name.split('@')
    run_id = int(name[0])
    contest_id = int(name[1])
    return Contest(contest_id).Run(run_id)
