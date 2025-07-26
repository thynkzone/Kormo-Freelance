from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


def send_mail(to, template, context, priority='normal'):
    try:
        logger.info(f"Attempting to send email to {to} using template {template}")
        logger.info(f"Email context: {context}")
        
        html_content = render_to_string(f'accounts/emails/{template}.html', context)
        text_content = render_to_string(f'accounts/emails/{template}.txt', context)
        
        logger.info(f"Templates rendered successfully. HTML length: {len(html_content)}, Text length: {len(text_content)}")

        # Set email headers for priority and importance
        headers = {
            'Importance': 'high' if priority == 'high' else 'normal',
            'Priority': 'urgent' if priority == 'high' else 'normal',
            'X-Priority': '1' if priority == 'high' else '3',
            'X-MSMail-Priority': 'High' if priority == 'high' else 'Normal',
        }

        msg = EmailMultiAlternatives(
            context.get('subject', 'No Subject'),
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [to],
            headers=headers,
        )
        msg.attach_alternative(html_content, 'text/html')
        
        logger.info(f"Email message prepared. From: {settings.DEFAULT_FROM_EMAIL}, To: {to}")
        logger.info(f"Email settings - Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}, TLS: {settings.EMAIL_USE_TLS}")
        
        msg.send()
        logger.info(f"Email sent successfully to {to} with template {template}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to} with template {template}: {str(e)}", exc_info=True)
        raise


def send_activation_email(request, email, code):
    context = {
        'subject': _('Profile activation'),
        'uri': request.build_absolute_uri(reverse('accounts:activate', kwargs={'code': code})),
    }

    send_mail(email, 'activate_profile', context, priority='high')


def send_activation_change_email(request, email, code):
    context = {
        'subject': _('Change email'),
        'uri': request.build_absolute_uri(reverse('accounts:change_email_activation', kwargs={'code': code})),
    }

    send_mail(email, 'change_email', context)


def send_reset_password_email(request, email, token, uid):
    context = {
        'subject': _('Restore password'),
        'uri': request.build_absolute_uri(
            reverse('accounts:restore_password_confirm', kwargs={'uidb64': uid, 'token': token})),
    }

    send_mail(email, 'restore_password_email', context, priority='high')


def send_contract_to_sign_email(request, contract):
    """Send email notification when a contract needs to be signed"""
    client_name = contract.job.created_by.freelancer.fullname if hasattr(contract.job.created_by, 'freelancer') and contract.job.created_by.freelancer else contract.job.created_by.username
    
    context = {
        'subject': _('Contract Ready for Your Signature'),
        'user': contract.freelancer,
        'job': contract.job,
        'client_name': client_name,
        'amount': contract.amount,
        'contract_url': request.build_absolute_uri(
            reverse('job:contract', kwargs={'job_id': contract.job.id, 'freelancer_id': contract.freelancer.id})
        ),
    }
    
    send_mail(contract.freelancer.email, 'contract_to_sign', context, priority='high')


def send_contract_signed_email(request, contract, signer):
    """
    Send email notification when a contract is signed
    """
    try:
        # Get the recipient (the other party who didn't sign)
        recipient = contract.job.created_by if signer == contract.freelancer else contract.freelancer
        
        # Get signer's name
        signer_name = signer.freelancer.fullname if hasattr(signer, 'freelancer') and signer.freelancer else signer.username
        
        # Prepare email context
        context = {
            'subject': 'Contract Signed Successfully',
            'user': recipient,
            'job': contract.job,
            'contract': contract,
            'signer': signer,
            'signer_name': signer_name,
            'amount': contract.amount,
            'signed_date': contract.freelancer_signed_at if signer == contract.freelancer else contract.client_signed_at,
            'contract_url': request.build_absolute_uri(reverse('job:contract', args=[contract.job.id, contract.freelancer.id]))
        }
        
        # Send the email using positional arguments
        send_mail(recipient.email, 'contract_signed', context, priority='high')
        
        logger.info(f"Contract signed email sent successfully to {recipient.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send contract signed email: {str(e)}")
        return False


def send_subscription_activated_email(request, subscription):
    """Send email notification when a subscription is activated"""
    try:
        logger.info(f"Preparing subscription activation email for user {subscription.user.email}")
        
        context = {
            'subject': _('Your subscription has been activated'),
            'user': subscription.user,
            'plan': subscription.plan,
            'start_date': subscription.created_at,
            'end_date': subscription.end_date,
            'profile_url': request.build_absolute_uri(reverse('freelancer:edit', kwargs={'pk': subscription.user.freelancer.pk})),
        }
        
        logger.info(f"Subscription email context prepared: {context}")
        result = send_mail(subscription.user.email, 'subscription_activated', context)
        logger.info(f"Subscription activation email sent successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send subscription activation email: {str(e)}", exc_info=True)
        raise


def send_job_reviewed_email(request, review):
    """Send email notification when a job is reviewed"""
    reviewer_name = review.reviewer.freelancer.fullname if hasattr(review.reviewer, 'freelancer') and review.reviewer.freelancer else review.reviewer.username
    
    context = {
        'subject': _('Your Job Has Been Reviewed'),
        'user': review.for_user,
        'job': review.job,
        'reviewer': review.reviewer,
        'reviewer_name': reviewer_name,
        'rating': review.rating,
        'content': review.content,
        'is_client_review': review.reviewer == review.job.created_by,
        'knowledge_depth': review.knowledge_depth,
        'fast_turnaround': review.fast_turnaround,
        'multiple_revisions': review.multiple_revisions,
        'quality_of_work': review.quality_of_work,
        'responsiveness': review.responsiveness,
        'communication': review.communication,
        'timely_replies': review.timely_replies,
        'requirements_detail': review.requirements_detail,
        'instant_feedback': review.instant_feedback,
        'logical_revisions': review.logical_revisions,
        'review_url': request.build_absolute_uri(
            reverse('job:detail', kwargs={'pk': review.job.id})
        ),
    }
    
    send_mail(review.for_user.email, 'job_reviewed', context)


def send_payment_verified_email(request, payment):
    """Send email notification when a payment is verified"""
    client_name = payment.job.created_by.freelancer.fullname if hasattr(payment.job.created_by, 'freelancer') and payment.job.created_by.freelancer else payment.job.created_by.username
    
    context = {
        'subject': _('Payment Verified'),
        'user': payment.job.created_by,
        'job': payment.job,
        'client_name': client_name,
        'amount': payment.amount,
        'transaction_id': payment.transaction_id,
        'payment_method': 'bKash',
        'verified_at': payment.verified_at,
        'job_url': request.build_absolute_uri(
            reverse('job:detail', kwargs={'pk': payment.job.id})
        ),
    }
    
    send_mail(payment.job.created_by.email, 'payment_verified', context)
    
    # Also notify the freelancer
    if payment.job.hired_freelancer:
        freelancer_context = context.copy()
        freelancer_context['user'] = payment.job.hired_freelancer
        freelancer_context['subject'] = _('Payment Received for Your Job')
        send_mail(payment.job.hired_freelancer.email, 'payment_verified', freelancer_context)


def send_job_invite_email(request, job, freelancer):
    """Send email notification when a freelancer is invited to a job"""
    client = job.created_by
    client_name = client.freelancer.fullname if hasattr(client, 'freelancer') and client.freelancer else client.username
    
    context = {
        'subject': _('You\'ve Been Invited to a Job!'),
        'user': freelancer,
        'job': job,
        'client_name': client_name,
        'job_url': request.build_absolute_uri(reverse('job:detail', kwargs={'pk': job.id})),
    }
    
    send_mail(freelancer.email, 'job_invite', context)