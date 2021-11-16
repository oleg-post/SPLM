# -*- coding: utf-8 -*-

import json
import os
from urllib.parse import quote, unquote
from flask import Blueprint, request, render_template, flash, g, session, redirect, url_for
from flask.views import MethodView
from flask_login import current_user, login_user, logout_user, login_required
from sqlalchemy.exc import NoResultFound
from werkzeug.urls import url_parse
from app.app_api import tsc_query
from app import app_api
from app.user_mgt.user_conf import UserConf
from app.user_mgt.models.users import db, User
from app.user_mgt.models.roles import Role
onto_mod_api = app_api.get_mod_api('onto_mgt')

url_prefix='/datanav'
MOD_NAME = 'data_navigation'
mod = Blueprint(MOD_NAME, __name__, url_prefix='/',
                template_folder=os.path.join(os.path.dirname(__file__),'templates'))

_auth_decorator = app_api.get_auth_decorator()


def getParent(cur_class, argms, list_of_templates):

    if any(argms['prefix'] in sl for sl in onto_mod_api.get_prefixes()):

        class_name = onto_mod_api.get_parent(argms['prefix'],cur_class)

        if class_name != '' and class_name not in list_of_templates:
            new_class = getParent(class_name, argms, list_of_templates)
        else:
            new_class = class_name
    else:
        new_class = ''

    return new_class

@mod.route(url_prefix)
@_auth_decorator
def startPage():
    heading = 'Стартовая страница'
    message1 = 'Стандартная навигация'
    message2 = 'Альтернативная навигация по дереву онтологии с кореневого класса "Thing"'

    page_stat = {'pizza':['<http://www.co-ode.org/ontologies/pizza/pizza.owl#Pizza>',
                          '<img src="/static/files/images/Pizza.png" width="200" height="200" alt="Pizza">',
                          '<a href="datanav/Pizza?prefix=pizza">Пицца</a>'],
                 'topping':['<http://www.co-ode.org/ontologies/pizza/pizza.owl#PizzaTopping>',
                            '<img src="/static/files/images/PizzaTopping.png" width="200" height="200" alt="PizzaTopping">',
                            '<a href="datanav/PizzaTopping?prefix=pizza">Топпиг</a>'],
                 'base':['<http://www.co-ode.org/ontologies/pizza/pizza.owl#PizzaBase>',
                         '<img src="/static/files/images/PizzaBase.png" width="200" height="200" alt="PizzaBase">',
                         '<a href="datanav/PizzaBase?prefix=pizza">Основа для пицца</a>']}

    stat = {}
    for key, val in page_stat.items():
        q_inst = tsc_query('mod_data_navigation.index.count_instances',{'URI':val[0]})
        q_cls = tsc_query('mod_data_navigation.index.count_subclasses',{'URI':val[0]})
        stat.update({key:{'inst':q_inst[0]['inst_qnt'], 'cls':q_cls[0]['cls_qnt'], 'img':val[1], 'href':val[2]}})

    return render_template("/index.html", heading=heading, stat=stat, message1=message1, message2=message2)

@mod.route(url_prefix + '/<class_object>')
@_auth_decorator
def uri_class(class_object):
    # cls = ''
    # new_class = ''
    list_of_templates = ['Thing']

    # Берем необходимые аргументы из http запроса
    argms = request.args.to_dict()
    argms['class'] = class_object

    # Если префикс онтологии не указан, то назначаем префикс по умолчанию "onto"
    if not 'prefix' in argms.keys():
        argms['prefix'] = 'onto'

    # Собираем все классы Питона, которые созданы для отображения классов онтологии из соответствующей папки
    for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__),'classes',argms['prefix'])):
        for _file in files:
            k = _file.rindex(".")
            if _file[k:] == ".py":
                list_of_templates.append(_file[:k])

    # Если у текущего класса онтологии нет шаблона, то ищем ближайший по иерархии родительский класс онтологии
    # у которого есть шаблон и переопределяем текущий класс на найденного родителя
    if class_object not in list_of_templates:
        class_with_tmpl = getParent(class_object, argms, list_of_templates)
    else:
        class_with_tmpl = class_object

    """ 
    Обрабатываем классы 
    согласно указанному префиксу
    """
    if argms['prefix'] == 'onto':  # ---------------------- ONTO ------------------------
        if class_with_tmpl == 'Document':
            from .classes.onto.Document import Document
            cls = Document(argms)
        # Добавляем сюда все варианты пренастроенных шаблонов коассов для префикса ONTO
        # elif _____:

        # Назначаем шаблон самого верхнего класса, который всегда должен быть
        elif class_with_tmpl == 'Thing':
            # Если есть прямое обращение к классу Thing с неправильным префиксом, то выдаем сообщение об ошибке
            if class_object == 'Thing':
                from .classes.onto.Blank import Blank
                cls = Blank(class_with_tmpl, 'NO class "%s" for the prefix "ONTO"' % argms['class'])
            else:
                from .classes.owl.Thing import Thing
                cls = Thing(argms)
        else:
            from .classes.onto.Blank import Blank
            cls = Blank(class_with_tmpl, 'NO class "%s" for the prefix "%s"' % (argms['class'], argms['prefix']))

    elif argms['prefix'] == 'pizza': # ---------------------- PIZZA ------------------------
        if class_with_tmpl == 'Pizza':
            from .classes.pizza.Pizza import Pizza
            cls = Pizza(argms)
        elif class_with_tmpl == 'PizzaTopping':
            from .classes.pizza.PizzaTopping import PizzaTopping
            cls = PizzaTopping(argms)
        elif class_with_tmpl == 'PizzaBase':
            from .classes.pizza.PizzaBase import PizzaBase
            cls = PizzaBase(argms)
        # Добавляем сюда все варианты пренастроенных шаблонов коассов для префикса ONTO
        # elif _____:

        elif class_with_tmpl == 'Thing':
            if class_object == 'Thing':
                from .classes.onto.Blank import Blank
                cls = Blank(class_with_tmpl, 'Нет класса "%s" в онтологии с префиксом "%s"' % (argms['class'], argms['prefix']))
            else:
                from .classes.owl.Thing import Thing
                cls = Thing(argms)
        else:
            from .classes.onto.Blank import Blank
            cls = Blank(class_with_tmpl, 'Нет класса "%s" в онтологии с префиксом "%s"' % (argms['class'], argms['prefix']))

    elif argms['prefix'] == 'owl': # ---------------------- OWL ------------------------
        if class_with_tmpl == 'Thing':
            from .classes.owl.Thing import Thing
            cls = Thing(argms)
        else:
            from .classes.onto.Blank import Blank
            cls = Blank(class_with_tmpl, 'Нет класса "%s" в онтологии с префиксом "OWL"' % argms['class'] )

    else: # ---------------------- ????????? ------------------------
        from .classes.onto.Blank import Blank
        cls = Blank(class_with_tmpl, 'Незарегистрированный префикс "%s"' % argms['prefix'] )

    return cls.getTemplate()
