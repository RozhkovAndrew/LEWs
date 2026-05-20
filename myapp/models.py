from myapp import db

class EWord(db.Model):
    __tablename__ = 'e_words'

    id=db.Column(db.Integer, primary_key=True)
    e_word=db.Column(db.String(50),index=True,unique=True)
    translations = db.relationship("Translation", backref='e_word_tr', cascade='all, delete-orphan')

    def __repr__(self):
        return '<{}>'.format(self.e_word)

class SubjectArea(db.Model):
    __tablename__ = 'subject_areas'
    id=db.Column(db.Integer, primary_key=True)
    subject_name=db.Column(db.String(50),index=True,unique=True)
    subject_def=db.Column(db.String(150))

    translations = db.relationship("Translation", backref='subject_area')

    def __repr__(self):
        return '<{}>'.format(self.subject_name)

class Translation(db.Model):
    __tablename__ = 'translations'

    id=db.Column(db.Integer, primary_key=True)
    translate_word=db.Column(db.String(80),index=True)
    definition_ru=db.Column(db.String(220))
    definition_en=db.Column(db.String(220))

    e_word_id=db.Column(db.Integer, db.ForeignKey('e_words.id'))
    subject_id=db.Column(db.Integer, db.ForeignKey('subject_areas.id'), nullable=False)

    #subject=db.relationship("SubjectArea", backref='subject_translations',foreign_keys=[subject_id])
    #e_word=db.relationship("EWord", backref='e_word_translations',foreign_keys=[e_word_id])


    def __repr__(self):
        return '<{}>'.format(self.translate_word)

