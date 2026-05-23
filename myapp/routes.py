from myapp import app
from flask import render_template, redirect, url_for, request, session, flash, abort
from sqlalchemy import func
from myapp.models import db, SubjectArea, EWord, Translation
import random
import git
import hmac
import hashlib
import json
import os

def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

#Webhook на обновление репозитория
@app.route('/update_server_gh', methods=['POST'])
def webhook():
    w_secret = os.environ['WEBHOOK_SECRET']
    if request.method != 'POST':
        return 'OK'
    else:
        abort_code = 418
        # Do initial validations on required headers
        if 'X-Github-Event' not in request.headers:
            abort(abort_code)
        if 'X-Github-Delivery' not in request.headers:
            abort(abort_code)
        if 'X-Hub-Signature' not in request.headers:
            abort(abort_code)
        if not request.is_json:
            abort(abort_code)
        if 'User-Agent' not in request.headers:
            abort(abort_code)
        ua = request.headers.get('User-Agent')
        if not ua.startswith('GitHub-Hookshot/'):
            abort(abort_code)

        event = request.headers.get('X-GitHub-Event')
        if event == "ping":
            return json.dumps({'msg': 'Hi!'})
        if event != "push":
            return json.dumps({'msg': "Wrong event type"})

        x_hub_signature = request.headers.get('X-Hub-Signature')
        # webhook content type should be application/json for request.data to have the payload
        # request.data is empty in case of x-www-form-urlencoded
        if not is_valid_signature(x_hub_signature, request.data, w_secret):
            print('Deploy signature failed: {sig}'.format(sig=x_hub_signature))
            abort(abort_code)

        payload = request.get_json()
        if payload is None:
            print('Deploy payload is empty: {payload}'.format(
                payload=payload))
            abort(abort_code)

        if payload['ref'] != 'refs/heads/main':
            return json.dumps({'msg': 'Not main; ignoring'})
        repo = git.Repo('.')
        origin = repo.remotes.origin
        origin.pull()
        return 'Updated PythonAnywhere successfully', 200

#Главная страница с приветствием
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

#Список всех слов, поиск и переход на добавление новых слов и категорий
@app.route('/words', methods=['GET'])
def words():
    #subjects = SubjectArea.query.all()
    subjects = db.session.query(SubjectArea.id, SubjectArea.subject_name, func.count(Translation.subject_id).label('count_translate')).join(Translation, Translation.subject_id == SubjectArea.id).group_by(SubjectArea.id, SubjectArea.subject_name).all()

    words=db.session.query(EWord).all()
    id_word = session.get('id_word')

    for word in words:
        translate_list=[]
        subject_list=[]
        subject_list_id=[]
        definition_en_list=[]
        definition_ru_list=[]
        translate_words = db.session.query(Translation.id, Translation.translate_word,Translation.definition_en, Translation.definition_ru, Translation.subject_id, SubjectArea.subject_name).join(Translation, Translation.subject_id == SubjectArea.id).filter_by(e_word_id=word.id)
        for translate_word in translate_words:
            subject_list_id.append(translate_word.subject_id)
            subject_list.append(translate_word.subject_name)
            translate_list.append(translate_word.translate_word)
            definition_en_list.append(translate_word.definition_en)
            definition_ru_list.append(translate_word.definition_ru)
           
        # Добавляем поля к слову
        word.subject_list = subject_list
        word.subject_list_id = subject_list_id
        word.translate_list = translate_list
        word.definition_en_list = definition_en_list
        word.definition_ru_list = definition_ru_list

    return render_template('words.html', words=words, subjects=subjects, id_word=id_word)

#Корректировка предметной области (категории)
@app.route('/add_subj', methods=['GET', 'POST'])
def add_subj():
    if request.method == 'POST':
        action = request.form.get('action')
        # Получаем данные из формы
        subject_name = request.form.get('subj_name')
        subject_def = request.form.get('subj_def')
        subj = db.session.query(SubjectArea).filter_by(subject_name=subject_name).first()
                
        if subject_name:
            if action == 'update':
                # Проверка на уникальность и выбор Добавить или Обновить
                if subj:
                    subj.subject_def=subject_def
                    flash('Предметная область обновлена!', 'success')
                else:
                    new_subj = SubjectArea(
                        subject_name=subject_name,
                        subject_def=subject_def
                    )
                    db.session.add(new_subj)
                    flash('Предметная область успешно создана!', 'success')

            elif action == 'delete':
                if subj and subj.id !=1:
                    db.session.delete(subj)
                    flash('Предметная область удалена!', 'success')

            db.session.commit()
   
    # Если GET запрос - показываем форму
    subjects = SubjectArea.query.all()
    return render_template('add_subj.html',subjects=subjects)

#Корректировка/добавление слова
@app.route('/add_word', defaults={'id': None}, methods=['GET', 'POST'])
@app.route('/add_word/<int:id>', methods=['GET','POST'])
def add_word(id):
    if request.method == 'POST':
        action = request.form.get('action')
        # Получаем данные из формы
        e_word = request.form.get('e_word')  #1.2
        id_word = 0 if request.form.get('id_word')=="" else int(request.form.get('id_word'))
        exist_word = db.session.query(EWord).filter_by(e_word=e_word).first()
            #Может быть по несколько значений
        id_translates= request.form.getlist('id_translate') #2.1
        subj_ids= request.form.getlist('subj_id')             #2.6
        translate_words= request.form.getlist('translate_word') #2.2
        definition_ens= request.form.getlist('definition_en')   #2.3
        definition_rus= request.form.getlist('definition_ru')   #2.4

        # Удаляет слово и переводы к нему из словаря
        if action == 'delete_word':
            word_delete = db.session.query(EWord).filter(EWord.id == id_word).first()
            db.session.delete(word_delete)
            db.session.commit()
            flash('Слово {0} удалено!'.format(e_word), 'success')
            return redirect(url_for('words'))

        #! Обновляет выбранный (походу все будут выбраны) перевод - и можно удалять по недостающим id - и добавлять новый перевод (нужно подумать насчет сессий при корявом вводе)
        if action == 'update_word' and not(all(item == "" for item in translate_words)):   
            #Новое слово и перевод к нему
            if e_word and translate_words and subj_ids and (id_word == 0) and (exist_word is None):
                #Добавляем слово в БД
                new_word = EWord(e_word=e_word)
                db.session.add(new_word)
                db.session.commit()
                
                #Добавляем переводы в БД
                for i in range(len(translate_words)):
                    translate_word = translate_words[i].strip()
                    subj_id = int(subj_ids[i].strip())
                    definition_en = definition_ens[i].strip()
                    definition_ru = definition_rus[i].strip()

                    if translate_word !="":
                        new_translate=Translation(translate_word=translate_word,subject_id=subj_id,definition_ru=definition_ru,definition_en=definition_en,e_word_id=new_word.id)
                        db.session.add(new_translate)
                        db.session.commit()
                flash('Слово {} добавлено в словарь!'.format(e_word), 'success')
                return redirect(url_for('add_word'))
            
            # Исправление самого слова, если было произведено и возможно
            elif e_word and (exist_word is None) and (e_word != exist_word):
                word_up = db.session.query(EWord).filter(EWord.id == id_word).first()
                word_up.e_word = e_word
                db.session.commit()
                
            # Обновление переводов (или удаление)
            for i in range(len(translate_words)):
                translate_word = translate_words[i].strip()
                translate_id = 0 if id_translates[i].strip()=="" else int(id_translates[i].strip())
                subj_id = int(subj_ids[i].strip())
                definition_ru = definition_rus[i].strip()
                definition_en = definition_ens[i].strip()
                
                if translate_word !="":
                    if translate_id==0:
                        new_translate=Translation(translate_word=translate_word,subject_id=subj_id,definition_ru=definition_ru,definition_en=definition_en,e_word_id=id_word)
                        db.session.add(new_translate)
                        db.session.commit()
                    else:
                        translate_up = db.session.get(Translation, translate_id)
                        if translate_up:
                            translate_up.translate_word = translate_word
                            translate_up.subject_id = subj_id
                            translate_up.definition_ru = definition_ru
                            translate_up.definition_en = definition_en
                            db.session.commit()
                else:
                    # Удаляем по отсутствующему тексту в переводе
                    translate_delete = db.session.get(Translation, translate_id)
                    db.session.delete(translate_delete)
                    db.session.commit()
            # сохраняем для отображения - передумал (но может пригодиться)
            session['id_word']=id_word
            flash('Корректировка {0} прошла успешно!'.format(e_word), 'success')
            return redirect(url_for('words'))

    # Для GET и всех действий
    #e_word_id = id if id is not None else session.pop('id_word', 0)
    e_word_id = id if id is not None else 0
    exist_word = db.session.query(EWord).filter_by(id=e_word_id)
    translate_words = db.session.query(Translation.id, Translation.translate_word,Translation.definition_en, Translation.definition_ru, Translation.subject_id, SubjectArea.subject_name).join(Translation, Translation.subject_id == SubjectArea.id).filter_by(e_word_id=e_word_id)

    subjects = SubjectArea.query.all()
    if exist_word:
        return render_template('add_word.html',subjects=subjects, words=exist_word, translates=translate_words)
    else:
        return render_template('add_word.html',subjects=subjects)
    
#Проверка знаний - подготовка
@app.route('/checkup', methods=['GET', 'POST'])
def checkup():
    if request.method == 'POST':
        subject_id = request.form.get('subj_id') 
        checkVar = int(request.form.get('checkVar'))
        numQT= int(request.form.get('numQuest'))  
        session['subject_id_session']=subject_id
        session['numQT_session']=numQT

        if checkVar == 1:
            return redirect(url_for('exam'))
        elif checkVar == 2:
            return redirect(url_for('exam_test'))

    # Отображение подготовки (или результата теста - может результат тоже выкинуть туда? чтобы не таскать данные делеко, а сразу там и отобразить)
    subjects = db.session.query(Translation.subject_id, SubjectArea.subject_name, func.count(Translation.subject_id).label('count_translate')).join(Translation, Translation.subject_id == SubjectArea.id).group_by(Translation.subject_id, SubjectArea.subject_name).all()
    return render_template('checkup.html',subjects=subjects)

#Проверка по точному ответу и результат
@app.route('/exam', methods=['GET', 'POST'])
def exam():
    numQT = session.pop('numQT_session', 1)
    subject_id = session.pop('subject_id_session', 1)
    # Запрос на слова с переводом нужной категории и формирование теста
    words = db.session.query(EWord.e_word, Translation.translate_word).join(Translation, EWord.id== Translation.e_word_id).filter(Translation.subject_id == subject_id).all()
    # Если вдруг было несколько переводов в одной категории
    numQT = min(numQT, len(words))
    test = random.sample(words, numQT)

    return render_template('exam.html',numQT=numQT, test=test)

#Проверка по тесту и результат
@app.route('/exam_test', methods=['GET', 'POST'])
def exam_test():
    numQT = session.pop('numQT_session', 1)
    subject_id = session.pop('subject_id_session', 1)
    varAns = 4 # вариантов на выбор
    # Запрос на слова с переводом нужной категории и формирование теста
    
    words = db.session.query(EWord.e_word, Translation.translate_word).join(Translation, EWord.id== Translation.e_word_id).filter(Translation.subject_id == subject_id).all()
    # Если вдруг было несколько переводов в одной категории
    numQT = min(numQT, len(words))
    test_words = random.sample(words, numQT)

    test_data = [] #новый список

    for word in test_words:
        var_words=[word.e_word]
        allwords = db.session.query(EWord.e_word).filter(EWord.e_word != word.e_word).all()
        allwords_str = [w[0] for w in allwords]
        wr_words = random.sample(allwords_str, varAns-1) # выбираем 3 неправильных варианта
        var_words = var_words + wr_words     # добавляем к правильному варианту неправильные
        var_words = random.sample(var_words, varAns) # перемешать перед отправкой

        # Сохраняем в список на отправку
        test_data.append({
            'e_word': word.e_word,
            'translate_word': word.translate_word,
            'var_words': var_words
        })

    return render_template('exam_test.html',numQT=numQT, test=test_data)
