from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(200))
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Ban/Suspend fields
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    ban_reason = db.Column(db.String(255))
    ban_expires_at = db.Column(db.DateTime)
    banned_at = db.Column(db.DateTime)
    banned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    suspension_type = db.Column(db.Enum('none', 'temporary', 'permanent', name='suspension_type_enum'), 
                              default='none', nullable=False)
    suspension_until = db.Column(db.DateTime)
    
    # Relationships
    banned_by = db.relationship('User', remote_side=[id], backref='banned_users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def is_banned_now(self):
        if not self.is_banned:
            return False
        if self.suspension_type == 'permanent':
            return True
        if self.suspension_type == 'temporary' and self.suspension_until:
            return datetime.utcnow() < self.suspension_until
        return False
    
    def get_ban_status(self):
        if not self.is_banned:
            return 'active'
        if self.suspension_type == 'permanent':
            return 'permanently_banned'
        if self.suspension_until and datetime.utcnow() < self.suspension_until:
            return 'temporarily_banned'
        return 'ban_expired'

class UserAction(db.Model):
    __tablename__ = 'user_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='actions')
