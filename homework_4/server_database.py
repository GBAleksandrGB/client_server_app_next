from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class ServerStorage:
    def __init__(self, path):
        self.database_engine = create_engine(f'sqlite:///{path}',
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
        name = Column(String, unique=True)
        last_login = Column(DateTime)

        def __init__(self, username):
            self.id = None
            self.name = username
            self.last_login = datetime.datetime.now()
            super().__init__()

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

    class UsersContacts(Base):
        __tablename__ = 'contacts'
        id = Column(Integer, primary_key=True)
        user = Column(ForeignKey('users.id'))
        contact = Column(ForeignKey('users.id'))

        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact
            super().__init__()

    class UsersHistory(Base):
        __tablename__ = 'history'
        id = Column(Integer, primary_key=True)
        user = Column(ForeignKey('users.id'))
        sent = Column(Integer)
        accepted = Column(Integer)

        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0
            super().__init__()

    def user_login(self, username, ip_address, port):
        # ???????????? ?? ?????????????? ?????????????????????????? ???? ?????????????? ?????? ???????????????????????? ?? ?????????? ????????????
        rez = self.session.query(self.AllUsers).filter_by(name=username)

        # ???????? ?????? ???????????????????????? ?????? ???????????????????????? ?? ??????????????, ?????????????????? ?????????? ???????????????????? ??????????
        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
        # ???????? ????????, ???? ???????????????????? ???????????? ????????????????????????
        else:
            user = self.AllUsers(username)
            self.session.add(user)
            # ?????????? ?????????? ??????????, ?????????? ???????????????????? ID
            self.session.commit()
            user_in_history = self.UsersHistory(user.id)
            self.session.add(user_in_history)

        # ???????????? ?????????? ?????????????? ???????????? ?? ?????????????? ???????????????? ?????????????????????????? ?? ?????????? ??????????.
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # ?? ?????????????????? ?? ?????????????? ????????????
        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        # ???????????????????? ??????????????????
        self.session.commit()

    # ?????????????? ?????????????????????? ???????????????????? ????????????????????????
    def user_logout(self, username):
        # ?????????????????????? ????????????????????????, ?????? ???????????????? ??????
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        # ?????????????? ?????? ???? ?????????????? ???????????????? ??????????????????????????.
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        # ?????????????????? ??????????????????
        self.session.commit()

    # ?????????????? ?????????????????? ???????????????? ?????????????????? ?? ???????????? ?????????????????????????????? ?????????????? ?? ????
    def process_message(self, sender, recipient):
        # ???????????????? ID ?????????????????????? ?? ????????????????????
        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id
        # ?????????????????????? ???????????? ???? ?????????????? ?? ?????????????????????? ????????????????
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        print(sender_row.sent)
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accepted += 1
        self.session.commit()

    # ?????????????? ?????????????????? ?????????????? ?????? ????????????????????????.
    def add_contact(self, user, contact):
        # ???????????????? ID ??????????????????????????
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # ?????????????????? ?????? ???? ?????????? ?? ?????? ?????????????? ?????????? ???????????????????????? (???????? ???????????????????????? ???? ????????????????)
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        # ?????????????? ???????????? ?? ?????????????? ?????? ?? ????????
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    # ?????????????? ?????????????? ?????????????? ???? ???????? ????????????
    def remove_contact(self, user, contact):
        # ???????????????? ID ??????????????????????????
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # ?????????????????? ?????? ?????????????? ?????????? ???????????????????????? (???????? ???????????????????????? ???? ????????????????)
        if not contact:
            return

        # ?????????????? ??????????????????
        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id).delete())
        self.session.commit()

    # ?????????????? ???????????????????? ???????????? ?????????????????? ?????????????????????????? ???? ???????????????? ???????????????????? ??????????.
    def users_list(self):
        # ???????????? ?????????? ?????????????? ??????????????????????????.
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login
        )
        # ???????????????????? ???????????? ????????????????
        return query.all()

    # ?????????????? ???????????????????? ???????????? ???????????????? ??????????????????????????
    def active_users_list(self):
        # ?????????????????????? ???????????????????? ???????????? ?? ???????????????? ?????????????? ??????, ??????????, ????????, ??????????.
        query = self.session.query(
            self.AllUsers.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        # ???????????????????? ???????????? ????????????????
        return query.all()

    # ?????????????? ?????????????????????????? ?????????????? ???????????? ???? ???????????????????????? ?????? ???????? ??????????????????????????
    def login_history(self, username=None):
        # ?????????????????????? ?????????????? ??????????
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.date_time,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # ???????? ???????? ?????????????? ?????? ????????????????????????, ???? ?????????????????? ???? ????????
        if username:
            query = query.filter(self.AllUsers.name == username)
        # ???????????????????? ???????????? ????????????????
        return query.all()

    # ?????????????? ???????????????????? ???????????? ?????????????????? ????????????????????????.
    def get_contacts(self, username):
        # ???????????????????????? ???????????????????? ????????????????????????
        user = self.session.query(self.AllUsers).filter_by(name=username).one()

        # ?????????????????????? ?????? ???????????? ??????????????????
        query = self.session.query(self.UsersContacts, self.AllUsers.name). \
            filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # ???????????????? ???????????? ?????????? ?????????????????????????? ?? ???????????????????? ????.
        return [contact[1] for contact in query.all()]

    # ?????????????? ???????????????????? ???????????????????? ???????????????????? ?? ???????????????????? ??????????????????
    def message_history(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        return query.all()


if __name__ == '__main__':
    test_db = ServerStorage('server_base.db3')
    test_db.user_login('user1', '192.168.1.113', 8080)
    test_db.user_login('user2', '192.168.1.113', 8081)
    print(test_db.users_list())
    # print(test_db.active_users_list())
    # test_db.user_logout('User1')
    # print(test_db.login_history('re'))
    # test_db.add_contact('test2', 'test1')
    # test_db.add_contact('test1', 'test3')
    # test_db.add_contact('test1', 'test6')
    # test_db.remove_contact('test1', 'test3')
    test_db.process_message('user1', 'user2')
    print(test_db.message_history())
