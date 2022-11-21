import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from homework_2.common.variables import SERVER_DB


Base = declarative_base()


class ServerStorage:
    def __init__(self):
        self.database_engine = create_engine(SERVER_DB,
                                             echo=False,
                                             pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.database_engine)
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    class AllUsers(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        username = Column(String, unique=True)
        last_login = Column(DateTime)

        def __init__(self, username):
            self.id = None
            self.username = username
            self.last_login = datetime.datetime.now()
            super().__init__()

        def __repr__(self):
            return f'{self.username} {self.last_login}'

    class ActiveUsers(Base):
        __tablename__ = 'active_users'
        id = Column(Integer, primary_key=True)
        user = Column(ForeignKey('users.id'), unique=True)
        ip_address = Column(String)
        port = Column(Integer)
        login_time = Column(DateTime)

        def __init__(self, user_id, ip_address, port, login_time):
            self.id = None
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            super().__init__()

        def __repr__(self):
            return f'{self.user} {self.ip_address} {self.port} {self.login_time}'

    class LoginHistory(Base):
        __tablename__ = 'login_history'
        id = Column(Integer, primary_key=True)
        name = Column(ForeignKey('users.id'))
        date_time = Column(DateTime)
        ip = Column(String)
        port = Column(String)

        def __init__(self, name, date, ip, port):
            self.id = None
            self.name = name
            self.date_time = date
            self.ip = ip
            self.port = port
            super().__init__()

        def __repr__(self):
            return f'{self.name} {self.date_time} {self.ip} {self.port}'

    class UserContacts(Base):
        __tablename__ = 'contacts'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('users.id'))
        contact = Column(String, ForeignKey('users.id'))

        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact
            super().__init__()

        def __repr__(self):
            return f'{self.user} {self.contact}'

    class UserHistory(Base):
        __tablename__ = 'history'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('users.id'))
        sent = Column(Integer)
        Accepted = Column(Integer)

        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0
            super().__init__()

        def __repr__(self):
            return f'{self.user} {self.sent} {self.accepted}'

    def user_login(self, username, ip_address, port):
        print(username, ip_address, port)
        rez = self.session.query(self.AllUsers).filter_by(username=username)

        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
        else:
            user = self.AllUsers(username)
            self.session.add(user)
            self.session.commit()

        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        self.session.commit()

    def user_logout(self, username):
        user = self.session.query(self.AllUsers).filter_by(username=username).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def process_message(self, sender, recipient):
        sender = self.session.query(self.AllUsers).filter_by(username=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(username=recipient).first().id
        sender_row = self.session.query(self.UserHistory).filter_by(name=sender).first()
        sender_row += 1
        recipient_row = self.session.query(self.UserHistory).filter_by(user=recipient).first()
        recipient_row += 1
        self.session.commit()

    def add_contact(self, user, contact):
        user = self.session.query(self.AllUsers).filter_by(username=user).first()
        contact = self.session.query(self.UserHistory).filter_by(contact=contact).first()

        if not contact or self.session.query(self.UserContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        contact_row = self.UserContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    def remove_contact(self, user, contact):
        user = self.session.query(self.AllUsers).filter_by(username=user).first()
        contact = self.session.query(self.AllUsers).filter_by(contact=contact).first()

        if not contact:
            return

        self.session.query(self.UserContacts).filter(
            self.UserContacts.user == user.id, self.UserContacts.contact == contact.id).delete()
        self.session.commit()

    def users_list(self):
        query = self.session.query(self.AllUsers.username, self.AllUsers.last_login)
        return query.all()

    def active_users_list(self):
        query = self.session.query(
            self.AllUsers.username,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time).join(self.ActiveUsers)
        return query.all()

    def login_history(self, username=None):
        query = self.session.query(self.AllUsers.username,
                                   self.LoginHistory.date_time,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port).join(self.AllUsers)

        if username:
            query = query.filter(self.AllUsers.username == username)

        return query.all()

    def get_contacts(self, username):
        user = self.session.query(self.AllUsers).filter_by(username=username).one()
        query = self.session.query(self.UserContacts, self.AllUsers.username).\
            filter_by(user=user.id).\
            join(self.AllUsers, self.UserContacts.contact == self.AllUsers.id)
        return [contact[1] for contact in query.all()]

    def message_history(self):
        query = self.session.query(
            self.AllUsers.username,
            self.AllUsers.last_login,
            self.UserHistory.sent,
            self.UserHistory.accepted).join(self.AllUsers)
        return query.all()


if __name__ == '__main__':
    test_db = ServerStorage()
    test_db.user_login('client_1', '192.168.1.5', 8000)
    test_db.user_login('client_2', '192.168.1.6', 7777)
    print(test_db.active_users_list())

    test_db.user_logout('client_1')
    print(test_db.active_users_list())

    print(test_db.login_history('client_1'))


