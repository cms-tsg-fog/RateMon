import sys
import copy
import datetime

from audioAlert import audioAlert
from mailAlert  import mailAlert
from colors import bcolors


class AlertStatus(object):
  DISABLED  = 0             # disabled
  READY     = 1             # enabled, not checked
  GOOD      = 2             # checked, no alarm conditions detected
  INVALID   = 3             # unable to check the alarm conditions
  SNOOZED   = 4             # checked, alarm conditions detected, suppressed by frequency limit
  ALARM     = 5             # checked, alarm conditions detected


class AlertLevel(object):
  NONE      = 0             # no alert
  INFO      = 1             # information message
  WARNING   = 2             # warning condition
  ERROR     = 3             # error condition

  color = {
    NONE:    bcolors.ENDC,
    INFO:    bcolors.OKGREEN,
    WARNING: bcolors.WARNING,
    ERROR:   bcolors.FAIL,
  }

  message = {
    NONE:    '',
    INFO:    '',
    WARNING: 'Warning',
    ERROR:   'Error',
  }


# Base class for any Alert.
# Implements the state machine logic for the alert status, and defines the interface for 
# accessing the alert messages.
# Subclasses should implement the condition logic, and the method to raise the alert.
class BaseAlert(object):

  def __init__(self, 
    enabled = True,         # if set to False, do not raise any alarm
    period  = 0.,           # do not raise an alarm more frequently than `period` seconds
    level   = None,         # if not None, the alert level associated to this Alert
    message = None,         # if not None, a short message warning about the Alert
    details = None,         # if not None, a longer messager giving details about the Alert
    actions = []            # list of functions to be called when the Alert is triggered
  ):
    self.__enabled = enabled
    self.__period  = period
    self.__level   = AlertLevel.NONE if level is None else level
    self.__message = message
    self.__details = details
    self.__actions = actions
    self.__status  = AlertStatus.READY
    self.__data    = dict()
    self.__stamp   = None   # track the last time this alarm was triggered

  # enable the Alert
  def enable(self):
    self.__enabled = True

  # disable the Alert
  def disable(self):
    self.__enabled = False

  # list the actions for this Alert
  def actions(self):
    return self.__actions

  # return the status of the Alert
  def status(self):
    return self.__status

  # reset the Alert to a READY status
  def reset(self):
    self.__status = AlertStatus.READY
    self.__data   = dict()

  # check if the alarm condition is active, i.e. the Alert is in status ALARM or SNOOZED
  def active(self):
    return self.status() in [ AlertStatus.SNOOZED, AlertStatus.ALARM ]

  # check if the alarm should be triggered, i.e. the Alert is in status ALARM
  def triggered(self):
    return self.status() == AlertStatus.ALARM

  # return the message corresponding to an active Alert, or None
  def alert_message(self):
    if not self.active():
      return None
    if not self.__message:
      return None
    header  = AlertLevel.message[self.__level]
    message = self.__message.format(** self.__data)
    if header:
      return header + ': ' + message
    else:
      return message

  # return the details corresponding to an active Alert, or None
  def alert_details(self):
    if not self.__details:
      return None
    return self.__details.format(** self.__data) if self.active() else None

  # return the level corresponding to an active Alert, or None
  def alert_level(self):
    return self.__level if self.active() else AlertLevel.NONE

  # return False if should raise an alarm
  def check(self, data):
    # copy the data for the error messages
    self.__data = copy.deepcopy(data)
    # check if the Alert is enabled
    if not self.__enabled:
      self.__status = AlertStatus.DISABLED
      return True
    # check the Alert condition
    self.__status = self.check_impl(self.__data)
    if self.__status != AlertStatus.ALARM:
      return True
    # check if the Alert has been triggered recently
    now = datetime.datetime.now()
    if (self.__stamp is not None) and (now - self.__stamp).total_seconds() < self.__period:
      self.__status = AlertStatus.SNOOZED
      return True
    # ready to trigger the Alert 
    self.__stamp = now
    return False

  # override this in derived classes to implement the actual checking behaviour
  def check_impl(self, data):
    return AlertStatus.INVALID

  # mark the Alert has having been triggered
  def snooze(self):
    self.__stamp = datetime.datetime.now()

  # raise the alarm(s)
  def alert(self):
    # check if there is an active alarm condition
    if not self.triggered():
      return

    # raise the alarm 
    self.snooze()
    for action in self.actions():
      action(self)


# combine multiple Alerts: check all of them, but raise an alarm only for the first active one
class PriorityAlert(BaseAlert):

  def __init__(self, *args, **kwargs):
    super(PriorityAlert, self).__init__(**kwargs)
    self.__alerts = args

  def check_impl(self, data):
    for alert in self.__alerts:
      alert.check(data)
    return max(alert.status() for alert in self.__alerts)

  def actions(self):
    for alert in self.__alerts:
      if alert.active():
        return alert.actions()
    return []

  def alert_message(self):
    for alert in self.__alerts:
      if alert.active():
        return alert.alert_message()
    return None
  
  def alert_details(self):
    for alert in self.__alerts:
      if alert.active():
        return alert.alert_details()
    return None
  
  def alert_level(self):
    for alert in self.__alerts:
      if alert.active():
        return alert.alert_level()
    return None
  
  def snooze(self):
    super(PriorityAlert, self).snooze()
    for alert in self.__alerts:
      if alert.active():
        alert.snooze()

  def reset(self):
    super(PriorityAlert, self).reset()
    for alert in self.__alerts:
      alert.reset()

      
# combine multiple Alerts: check all of them, and raise a combined alarm
class MultipleAlert(BaseAlert):

  def __init__(self, *args, **kwargs):
    super(MultipleAlert, self).__init__(**kwargs)
    self.__alerts = args

  # https://stackoverflow.com/a/480227/2050986
  @staticmethod
  def unique(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]

  # if different messages are about to be triggered, add an optional introduction and merge them
  @staticmethod
  def merged(messages, header = None):
    if len(messages) == 0:
      return None
    elif len(messages) == 1:
      return messages[0]
    else:
      messages = MultipleAlert.unique(messages)
      if header is not None:
        messages.insert(0, header)
      return '\n'.join(messages)

  # if different messages are about to be triggered, replace them with a single one
  @staticmethod
  def single(messages, header = None):
    if len(messages) == 0:
      return None
    elif len(messages) == 1:
      return messages[0]
    elif header is not None:
      return header
    else:
      return messages[0]

  def alert_message(self):
    if not self.active():
      return None
    header = super(MultipleAlert, self).alert_message()
    return self.single([ alert.alert_message() for alert in self.__alerts if alert.active() ], header)

  def alert_details(self):
    if not self.active():
      return None
    header = super(MultipleAlert, self).alert_details()
    return self.merged([ alert.alert_details() for alert in self.__alerts if alert.active() ], header)

  def alert_level(self):
    if not self.active():
      return AlertLevel.NONE
    level = super(MultipleAlert, self).alert_level()
    return max(level, *( alert.alert_level() for alert in self.__alerts if alert.active() ))

  def check_impl(self, data):
    for alert in self.__alerts:
      alert.check(data)
    return max(alert.status() for alert in self.__alerts)

  def actions(self):
    actions = list()
    for alert in self.__alerts:
      if alert.active():
        for other in alert.actions():
          if other not in actions:
            actions.append(other)
    return actions

  def snooze(self):
    super(MultipleAlert, self).snooze()
    for alert in self.__alerts:
      if alert.active():
        alert.snooze()

  def reset(self):
    super(MultipleAlert, self).reset()
    for alert in self.__alerts:
      alert.reset()


# trigger an email Alert
def EmailMessage(alert):
  message = alert.alert_message()
  details = alert.alert_details()
  level   = alert.alert_level()
  if message is not None:
    if details is not None:
      message = message + '\n\n' + details
    mailAlert(message)


# trigger an audio Alert
def AudioMessage(alert):
  message = alert.alert_message()
  details = alert.alert_details()
  level   = alert.alert_level()
  if message is not None:
    audioAlert(message, details)


# trigger an on screen Alert
def OnScreenMessage(alert):
  message = alert.alert_message()
  details = alert.alert_details()
  level   = alert.alert_level()
  color   = AlertLevel.color[level]
  if message is not None:
    print('%s%s%s' % (color, message, bcolors.ENDC))
    if details is not None:
      print(details)


# raise an alert if the value returned by calling `measure` with the argument passed to `check` is higher than `threshold`
class RateAlert(BaseAlert):

  def __init__(self,
    measure,                # a function object called to extract the "rate" to be monitored
    threshold,              # raise an alarm if the rate is higher than `threshold`
    *args, **kwargs
  ):
    super(RateAlert, self).__init__(*args, **kwargs)
    self.__measure   = measure
    self.__threshold = threshold

  def check_impl(self, data):
    try:
      value = self.__measure(data)
      if value > self.__threshold:
        return AlertStatus.ALARM
      else:
        return AlertStatus.GOOD
    except:
      return AlertStatus.INVALID


# raise an alert if the flag returned by calling `measure` with the argument passed to `check` is False
class FlagAlert(BaseAlert):

  def __init__(self,
    measure,                # a function object called to extract the flag to be monitored
    *args, **kwargs
  ):
    super(FlagAlert, self).__init__(*args, **kwargs)
    self.__measure = measure

  def check_impl(self, data):
    try:
      value = self.__measure(data)
      if value == False:
        return AlertStatus.ALARM
      else:
        return AlertStatus.GOOD
    except:
      return AlertStatus.INVALID


# test these methods
if __name__=='__main__':
  import time
  import math

  def get_rates(t):
    rates = {}
    rates['alpha'] = 2 - 2 * math.cos(t * 0.5)
    rates['bravo'] = 5 - 5 * math.cos(t * 0.3)
    rates['delta'] = 3 - 3 * math.cos(t * 0.2)
    rates['total'] = rates['alpha'] + rates['bravo'] + rates['delta']
    return rates

  w  = RateAlert(message = 'high rate',
                 details = 'high total rate\ntotal rate: {total}',
                 level   = AlertLevel.WARNING,
                 measure = lambda x: x['total'],
                 threshold = 10,
                 period = 10.,
                 actions = [EmailMessage, AudioMessage, OnScreenMessage])

  e  = RateAlert(message = 'critical rate',
                 details = 'critical total rate\ntotal rate: {total}',
                 level   = AlertLevel.ERROR,
                 measure = lambda x: x['total'],
                 threshold = 15,
                 period =  2.,
                 actions = [EmailMessage, AudioMessage, OnScreenMessage])

  p  = PriorityAlert(e, w)

  i1 = RateAlert(message = 'alpha rate',
                 details = 'alpha rate: {alpha}',
                 level   = AlertLevel.INFO,
                 measure = lambda x: x['alpha'],
                 threshold = 0,
                 period = 1.,
                 actions = [OnScreenMessage])

  i2 = RateAlert(message = 'bravo rate',
                 details = 'bravo rate: {bravo}',
                 level   = AlertLevel.INFO,
                 measure = lambda x: x['bravo'],
                 threshold = 0,
                 period = 1.,
                 actions = [OnScreenMessage])

  i3 = RateAlert(message = 'delta rate',
                 details = 'delta rate: {delta}',
                 level   = AlertLevel.INFO,
                 measure = lambda x: x['delta'],
                 threshold = 0,
                 period = 1.,
                 actions = [OnScreenMessage])


  ii = MultipleAlert(i1, i2, i3, message = 'multiple rates')
  m  = MultipleAlert(p, ii)

  for t in range(120):
    rates = get_rates(t)
    print
    print 'time:', t
    if not m.check(rates):
      m.alert()
    time.sleep(1)

