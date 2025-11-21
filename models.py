# models.py
from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    api_key = Column(Text, nullable=True)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    role = Column(String(16), nullable=False)
    text = Column(Text, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "role in ('user', 'assistant')",
            name="ck_message_role",
        ),
    )


class MediaPlanRow(Base):
    __tablename__ = "mediaplan_rows"

    id = Column(Integer, primary_key=True, index=True)

    # basic descriptors
    source = Column(String, nullable=True)
    type = Column(String, nullable=True)
    department = Column(String, nullable=True)
    bu_cost_center = Column(String, nullable=True)
    billed_cost_center = Column(String, nullable=True)
    cost_center = Column(String, nullable=True)
    business_unit = Column(String, nullable=True)
    business_internal = Column(String, nullable=True)
    revenue_type = Column(String, nullable=True)
    cc_costs_type = Column(String, nullable=True)
    bu_costs_type = Column(String, nullable=True)
    client = Column(String, nullable=True)
    client_status = Column(String, nullable=True)
    pm = Column(String, nullable=True)
    sm = Column(String, nullable=True)
    project_id = Column(String, nullable=True)
    project = Column(String, nullable=True)
    project_status = Column(String, nullable=True)
    category = Column(String, nullable=True)
    detail = Column(String, nullable=True)
    media_type = Column(String, nullable=True)
    paid_by = Column(String, nullable=True)

    # period
    month = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)

    # dates
    duzp = Column(Date, nullable=True)
    cf_date = Column(Date, nullable=True)
    dph_date = Column(Date, nullable=True)

    # mediaplan / invoicing
    id_mediaplan = Column(Integer, nullable=True)
    mediaplan = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    invoice_issue_date = Column(Date, nullable=True)
    invoice_due_date = Column(Date, nullable=True)
    invoice_payment_date = Column(Date, nullable=True)

    # forecast/meta
    forecast_level = Column(Integer, nullable=True)
    main_status = Column(String, nullable=True)
    finance_status = Column(String, nullable=True)
    cf_status = Column(String, nullable=True)
    probability = Column(Float, nullable=True)
    hours = Column(Float, nullable=True)

    # business context
    firma = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    cost_category = Column(String, nullable=True)
    fc_source = Column(String, nullable=True)
    fc_source_prepayments = Column(String, nullable=True)
    client_logo = Column(String, nullable=True)
    pm_email = Column(String, nullable=True)
    pm_picture = Column(String, nullable=True)

    # price_* (forecast / bp / revised / real)
    price_fc_revenues = Column(Float, nullable=True)
    price_fc_revenues_prepayments = Column(Float, nullable=True)
    price_fc_costs = Column(Float, nullable=True)
    price_fc_costs_prepayments = Column(Float, nullable=True)

    price_bp_revenues = Column(Float, nullable=True)
    price_bp_revenues_prepayments = Column(Float, nullable=True)
    price_bp_costs = Column(Float, nullable=True)
    price_bp_costs_prepayments = Column(Float, nullable=True)

    price_bp_revised_revenues = Column(Float, nullable=True)
    price_bp_revised_revenues_prepayments = Column(Float, nullable=True)
    price_bp_revised_costs = Column(Float, nullable=True)
    price_bp_revised_costs_prepayments = Column(Float, nullable=True)

    price_real_revenues = Column(Float, nullable=True)
    price_real_revenues_prepayments = Column(Float, nullable=True)
    price_real_revenues_findb = Column(Float, nullable=True)
    price_real_costs = Column(Float, nullable=True)

    # forecast_fc_* and cm
    forecast_fc_revenues = Column(Float, nullable=True)
    forecast_fc_revenues_prepayments = Column(Float, nullable=True)
    forecast_fc_costs = Column(Float, nullable=True)
    forecast_fc_costs_prepayments = Column(Float, nullable=True)
    forecast_fc_revenue_cm = Column(Float, nullable=True)
    forecast_fc_costs_cm = Column(Float, nullable=True)

    # up-to-date / mixed fc+real
    forecast_fc_real_up_to_date_revenues = Column(Float, nullable=True)
    forecast_fc_real_up_to_date_revenues_prepayments = Column(Float, nullable=True)
    price_fc_real_up_to_date_revenues_prepayments = Column(Float, nullable=True)
    forecast_fc_real_up_to_date_costs = Column(Float, nullable=True)
    forecast_fc_real_up_to_date_costs_prepayments = Column(Float, nullable=True)
    price_fc_real_up_to_date_costs_prepayments = Column(Float, nullable=True)
