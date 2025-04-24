group_members = db.Table(
    'group_members',
    db.Column('user_id',  db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)

class Group(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(80), unique=True, nullable=False)
    members  = db.relationship('User', secondary=group_members,
                               back_populates='groups')
    messages = db.relationship('Message', back_populates='group',
                               cascade='all, delete-orphan')

class Message(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id  = db.Column(db.Integer, db.ForeignKey('group.id'))
    content   = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user  = db.relationship('User', back_populates='messages')
    group = db.relationship('Group', back_populates='messages')

# on User model:
User.groups    = db.relationship('Group', secondary=group_members,
                                 back_populates='members')
User.messages  = db.relationship('Message', back_populates='user')
