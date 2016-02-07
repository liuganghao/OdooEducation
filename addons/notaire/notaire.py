# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
from datetime import datetime, timedelta, date
import datetime
from dateutil.relativedelta import relativedelta
import logging
import lxml
from urllib import urlencode, quote as quote
import urlparse

import convertion
import dateutil.relativedelta as relativedelta
from openerp import SUPERUSER_ID
from openerp import api, tools
from openerp import tools, api
import openerp
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import html2plaintext
from openerp.tools.translate import _
from openerp.tools.mail import plaintext2html


_logger = logging.getLogger(__name__)


def format_tz(pool, cr, uid, dt, tz=False, format=False, context=None):
    context = dict(context or {})
    if tz:
        context['tz'] = tz or pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz'] or "UTC"
    timestamp = datetime.datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)

    ts = fields.datetime.context_timestamp(cr, uid, timestamp, context)

    if format:
        return ts.strftime(format)
    else:
        lang = context.get("lang")
        lang_params = {}
        if lang:
            res_lang = pool.get('res.lang')
            ids = res_lang.search(cr, uid, [("code", "=", lang)])
            if ids:
                lang_params = res_lang.read(cr, uid, ids[0], ["date_format", "time_format"])
        format_date = lang_params.get("date_format", '%B-%d-%Y')
        format_time = lang_params.get("time_format", '%I-%M %p')

        fdate = ts.strftime(format_date)
        ftime = ts.strftime(format_time)
        return "%s %s%s" % (fdate, ftime, (' (%s)' % tz) if tz else '')

try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': quote,
        'urlencode': urlencode,
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': reduce,
        'map': map,
        'round': round,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")


class act_nature(osv.osv):
    _name = "act.nature"
    _description = "Nature de l acte"


    _columns = {
        'name': fields.char('Nature de l acte'),
        'contratmodel': fields.html('Modèle de Contrat', help='Automatically sanitized HTML contents'),
        'note': fields.text('Description'),
    }

act_nature()

class type_bien(osv.osv):
    _name = "type.bien"
    _description = "Type du bien"


    _columns = {
        'name': fields.char('type de bien'),
        'note': fields.text('Description'),
    }


    # Form filling
type_bien()

class dossier_state(osv.osv):
    _name = "dossier.state"
    _description = "Etat du dossier"


    _columns = {
        'name': fields.char('Etat du dossier'),
        'note': fields.text('Description'),
    }


    # Form filling

dossier_state()

class dossier_priority(osv.osv):
    _name = "dossier.priority"
    _description = "Priorite du dossier"


    _columns = {
        'name': fields.char(u'Priorité'),
        'note': fields.text('Description'),
    }


    # Form filling

dossier_priority()

class delay_reason(osv.osv):
    _name = "delay.reason"
    _description = "Les motifs des retards"

    _columns = {
        'name': fields.char(u'Motif de retard'),
        'note': fields.text('Description'),
    }


    # Form filling

delay_reason()


class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"
    _description = "Sales Order"

    def render_template_batch(self, cr, uid, template, model, res_ids, context=None, post_process=False):
        """Render the given template text, replace mako expressions ``${expr}``
           with the result of evaluating these expressions with
           an evaluation context containing:

                * ``user``: browse_record of the current user
                * ``object``: browse_record of the document record this mail is
                              related to
                * ``context``: the context passed to the mail composition wizard

           :param str template: the template text to render
           :param str model: model name of the document record this mail is related to.
           :param int res_ids: list of ids of document records those mails are related to.
        """
        if context is None:
            context = {}
        res_ids = filter(None, res_ids)         # to avoid browsing [None] below
        results = dict.fromkeys(res_ids, u"")

        # try to load the template
        try:
            template = mako_template_env.from_string(tools.ustr(template))
        except Exception:
            _logger.exception("Failed to load template %r", template)
            return results

        # prepare template variables
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        records = self.pool[model].browse(cr, uid, res_ids, context=context) or [None]
        variables = {
            'format_tz': lambda dt, tz=False, format=False, context=context: format_tz(self.pool, cr, uid, dt, tz, format, context),
            'user': user,
            'ctx': context,  # context kw would clash with mako internals
        }
        for record in records:
            res_id = record.id if record else None
            variables['object'] = record
            try:
                render_result = template.render(variables)
            except Exception:
                _logger.exception("Failed to render template %r using values %r" % (template, variables))
                render_result = u""
            if render_result == u"False":
                render_result = u""
            results[res_id] = render_result

        if post_process:
            for res_id, result in results.iteritems():
                results[res_id] = self.pool.get("email.template").render_post_process(cr, uid, result, context=context)
        return results

    def _body_parsing(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for sal in self.browse(cr, uid, ids, context=context):
################################# parsing code #########################################           
            if context is None:
                context = {}
            field = "body"
            template = self.browse(cr, uid, [sal.id], context=context)
            template_res_ids = [sal.id]
            ctx = context.copy()
            print "ctx -------------------------->", ctx
            generated_field_values = self.render_template_batch(
                    cr, uid, getattr(template, field), 'sale.order', template_res_ids,
                    post_process=(field == 'body'),
                    context=ctx)
            print "generated_field_values ------------------->", generated_field_values
##########################################################################################            
            for desc1, desc2 in generated_field_values.iteritems():
                print "res ====================>", desc2
                print "res2 ====================>", tools.plaintext2html(desc2)
            res[sal.id] = tools.plaintext2html(desc2)
        return res          
        
    def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):
        """ Wrapper because of direct method passing as parameter for function fields """
        return self._amount_all(cr, uid, ids, field_name, arg, context=context)
    
    def print_contract(self, cr, uid, ids, context=None):
        '''
        This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
        '''
################################# parsing code #########################################
        for sal in self.browse(cr,uid,ids,context=context):                   
            if context is None:
                context = {}
            field = "body"
            template = self.browse(cr, uid, [sal.id], context=context)
            template_res_ids = [sal.id]
            ctx = context.copy()
            generated_field_values = self.render_template_batch(
                    cr, uid, getattr(template, field), 'sale.order', template_res_ids,
                    post_process=(field == 'body'),
                    context=ctx)
            print "generated_field_values ------------------->", generated_field_values
            for desc1, desc2 in generated_field_values.iteritems():
                print "desc2 =============================>", desc2
            sal.write({'contrat': desc2})
        assert len(ids) == 1, 'This option should only be used for a single id at a time'

        return self.pool['report'].get_action(cr, uid, ids, 'notaire.report_contratnotaire', context=context)
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'frais_ecart': 0.0,
                'fond_ecart': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
            val_frais = val_frais1 = val_fond = val_fond1 = 0.0
            for line2 in order.transaction_ids:
                val_frais += line2.CFrais_Recettes
                val_frais1 += line2.CFrais_Depenses
                val_fond += line2.CFonds_Recettes
                val_fond1 += line2.CFonds_Depenses
            res[order.id]['sum_CFrais_Recettes'] = cur_obj.round(cr, uid, cur, val_frais)
            res[order.id]['sum_CFrais_Depenses'] = cur_obj.round(cr, uid, cur, val_frais1)
            res[order.id]['sum_CFonds_Recettes'] = cur_obj.round(cr, uid, cur, val_fond)
            res[order.id]['sum_CFonds_Depenses'] = cur_obj.round(cr, uid, cur, val_fond1)
            res[order.id]['frais_ecart'] = cur_obj.round(cr, uid, cur, val_frais - val_frais1)
            res[order.id]['fond_ecart'] = cur_obj.round(cr, uid, cur, val_fond - val_fond1)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res
    
    def _get_text_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for sal in self.browse(cr, uid, ids, context=context):
                amount = sal.amount_total
                text_amount = convertion.trad(amount, 'Dirham')
                res[sal.id] = text_amount.upper()              
        return res
    
    def on_change_natureact(self, cr, uid, ids,nature_acte,context=None):
        for line in self.pool.get('act.nature').browse(cr, uid, nature_acte, context=context):
            return {'value': {'body': line.contratmodel}}   
    
    def _get_text_superficie(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for sal in self.browse(cr, uid, ids, context=context):
                superficie = sal.superficie
                superficie_text = convertion.trad(superficie, '')
                res[sal.id] = superficie_text.upper()              
        return res
            
    def _get_state(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for sal in self.browse(cr, uid, ids, context=context):
            res[sal.id] = 1
            if sal.state=='non_enregistre' or sal.state=='minute':
                    if sal.date_signature:
                        current_date = datetime.date.today()
                        signature_date = sal.date_signature
                        signature_date = datetime.datetime.strptime(signature_date, DEFAULT_SERVER_DATE_FORMAT)
                        end_date = signature_date
                        end_date = end_date.date()
                        difference =  current_date - end_date
                        if difference.days < 7:
                            res[sal.id] = 1
                        else:
                            res[sal.id] = 2 
            else:
                if sal.state=='enregistre':
                    if sal.date_enrg:
                        current_date = datetime.date.today()
                        enrg_date = sal.date_enrg
                        enrg_date = datetime.datetime.strptime(enrg_date, DEFAULT_SERVER_DATE_FORMAT)
                        enrg_date = enrg_date.date()
                        difference =  current_date - enrg_date
                        if difference.days < 7:
                            res[sal.id] = 1
                        else:
                            res[sal.id] = 2 
        return res 
    #  Methods of the WorkFlow :
    
    def dossier_draft(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'state':'draft'})
        return True
    
    def dossier_minute(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'state':'minute'})
        return True
    
    def dossier_enregister(self, cr, uid, ids ,context=None):
        for sal in self.browse(cr, uid, ids, context=context):
            if sal.enrg_ok and sal.date_enrg:
                self.write(cr,uid,ids,{'state':'enregistre'})
        return True
    
    def dossier_rejete(self, cr, uid, ids ,context=None):
        self.write(cr,uid,ids,{'state':'rejete'})
        return True
    
    def dossier_enregister_none(self, cr, uid, ids ,context=None):
        for sal in self.browse(cr, uid, ids, context=context):
            if sal.date_signature:
                self.write(cr,uid,ids,{'state':'non_enregistre'})
            else :
                return False
        return True
    
    def dossier_conserve(self, cr, uid, ids ,context=None):
        for sal in self.browse(cr, uid, ids, context=context):
            if sal.enrg_ok and sal.cf_ok and sal.date_cf:
                self.write(cr,uid,ids,{'state':'conserve'})
        return True
        
    
    def dossier_done(self, cr, uid, ids ,context=None):
        self.write(cr,uid,ids,{'state':'termine'})
        return True
    
    def onchange_minute_state(self, cr, uid, ids ,context=None):
       self.write(cr,uid,ids,{'state':'non_enregistre'})
       return True
    
    _columns = {
        'repertory_name': fields.char('Reference/Description', copy=False),
        'seller_id': fields.many2one('res.partner', 'Vendeur', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, select=True, track_visibility='always'),
        'price_sell': fields.float('Prix / Vente', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'progress': [('readonly', False)]}),
        'loan_amount': fields.float('MT Pret', required=True, digits_compute=dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'progress': [('readonly', False)]}),
        'bank': fields.many2one('res.bank', 'Banque', states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'progress': [('readonly', False)]}, select=True, track_visibility='onchange'),
        'responsable_enrg': fields.many2one('res.users', 'Résponsable Enreg',select=True, track_visibility='onchange'),
        'responsable_depot_enrg' : fields.selection([
                                               ('yassine', 'Yassine'),
                                               ('hossaine', 'Hossaine'),
                                               ('issam', 'Issam'),
                                               ('Mohammed', 'Mohammed'),
                                               ], 'Chargé du Dépot'),
        'responsable_cf': fields.many2one('res.users', 'Résponsable CF', states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'progress': [('readonly', False)]}, select=True, track_visibility='onchange'),
        'responsable_depot_cf' : fields.selection([
                                               ('yassine', 'Yassine'),
                                               ('hossaine', 'Hossaine'),
                                               ('issam', 'Issam'),
                                               ('Mohammed', 'Mohammed'),
                                               ], 'Chargé du Dépot'),
        'responsable_quitus': fields.many2one('res.users', 'Charge QUITUS', states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'progress': [('readonly', False)]}, select=True, track_visibility='onchange'),
        'responsable_depot_quitus' : fields.selection([
                                               ('yassine', 'Yassine'),
                                               ('hossaine', 'Hossaine'),
                                               ('issam', 'Issam'),
                                               ('Mohammed', 'Mohammed'),
                                               ], 'Chargé du Dépot'),
        'date_depot_enrg': fields.date('Date de Depot', select=True, copy=False),
        'date_enrg': fields.date('Date ENRG', select=True, copy=False),
        'date_depot_cf': fields.date('Date de Depot', select=True, copy=False),
        'date_cf': fields.date('Date CF', select=True, copy=False),
        'body': fields.html('Contract Contents', sanitize=False, help='Automatically sanitized HTML contents'),
        'or': fields.char('O R'),
        're': fields.char('R E'),
        'dv': fields.char('D V'),
        'qce': fields.char('QCE'),
        'recu': fields.char('N de Recu'),
        'enrg_amount': fields.float('Montant', required=True, digits_compute=dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'progress': [('readonly', False)]}),
        'retrait_min': fields.float('Retrait Min', required=True, digits_compute=dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'progress': [('readonly', False)]}),
        'cf_amount': fields.float('Montant', required=True, digits_compute=dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'progress': [('readonly', False)]}),
        'certificat': fields.selection([
            ('oui', 'OUI'),
            ('non', 'NON'),
            ], 'Certificat', copy=False, select=True),
        'tute': fields.selection([
            ('oui', 'OUI'),
            ('non', 'NON'),
            ], 'T.U T.E', copy=False, select=True),
        'tnb': fields.selection([
            ('oui', 'OUI'),
            ('non', 'NON'),
            ], 'T.N.B', copy=False, select=True),
        'quitus_f': fields.selection([
            ('oui', 'OUI'),
            ('non', 'NON'),
            ], 'Quittance F', copy=False, select=True),
        'date_signature': fields.date('Date Signature', select=True, copy=False),
        'date_acquisition': fields.date('Date Acquisition', select=True, copy=False),
        'tf_req': fields.char('T.F  Requisition'),
        'tf_mee': fields.char('T.F  mere'),
        'alerte': fields.integer('Jours d alertes', help="Choisir le nombre de jours pour declencher l alerte"),
        'nature_acte': fields.many2one('act.nature', 'Nature de l acte', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},),
        'type_bien': fields.many2one('type.bien', 'Type du bien', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},),
        'adresse': fields.char('Adresse'),
        'ville': fields.char('Ville'),
        'superficie': fields.float('Superficie'),
        'etage': fields.char('Etage'),
        'etat_dossier': fields.many2one('dossier.state', 'Etat du dossier', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},),
        'priorite_dossier': fields.many2one('dossier.priority', 'Priorite dossier', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},),
        'devis_ok': fields.boolean('Devis Payé'),
        'enrg_ok': fields.boolean('ENRG OK'),
        'cf_ok': fields.boolean('CF OK'),
        'quitus_ok': fields.boolean('Quittance OK'),
        'n_enrg': fields.char('N ENRG'),
        'n_cf': fields.char('N CF'),
        'n_quitus': fields.char('N Quittance'),
       # 'amount_text': fields.function(_get_text_amount, method=True, type='text', string='Text amount',store=True ),
       # 'superficie_text': fields.function(_get_text_superficie, method=True, type='text', string='Text superficie',store=True ),
        'delay_reasons': fields.many2one('delay.reason', 'Motif de retard', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},),
       # Transaction relation 
        'transaction_ids': fields.one2many('notaire.dossier.transaction', 'transaction_id', 'Transactions'),
        'sum_CFrais_Recettes': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='sum_CFrais_Recettes',
            store=True,
            multi='sums', help="sum_CFrais_Recettes"),
        'sum_CFrais_Depenses': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='sum_CFrais_Depenses',
            store=True,
            multi='sums', help="sum_CFrais_Depenses"),
        'sum_CFonds_Recettes': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='sum_CFonds_Recettes',
            store=True,
            multi='sums', help="sum_CFonds_Recettes"),
        'sum_CFonds_Depenses': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='sum_CFonds_Depenses',
            store=True,
            multi='sums', help="sum_CFonds_Depenses"),
        'frais_ecart': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Frais',
            store=True,
            multi='sums', help="ecart fond"),
        'fond_ecart': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Fond',
            store=True,
            multi='sums', help="ecart fond"),
        'amount_text': fields.function(_get_text_amount, method=True, type='text', string='Text amount', store=True),
        'superficie_text': fields.function(_get_text_superficie, method=True, type='text', string='Text superficie', store=True),
        'state': fields.selection([
            ('draft', 'Dossier Brouillon'),
            ('minute', 'Minute'),
            ('non_enregistre', 'Non Enregistré'),
            ('enregistre', 'Enregistré'),
            ('conserve', 'Conservé'),
            ('rejete', 'Rejeté'),
            ('termine', 'Terminé'),
            ('sent', 'Quotation Sent'),
            ('cancel', 'Cancelled'),
            ('waiting_date', 'Waiting Schedule'),
            ('progress', 'Sales Order'),
            ('manual', 'Sale to Invoice'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ], 'Status', readonly=True, copy=False, help="Gives the status of the quotation or sales order.\
              \nThe exception status is automatically set when a cancel operation occurs \
              in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
               but waiting for the scheduler to run on the order date.", select=True),
        'signature_state': fields.function(_get_state, method=True, type='integer', string='state color',store=True ),
      #  'contrat': fields.function(_body_parsing, method=True, type='html', string='Contrat',store=True ),
        'contrat': fields.html('contrat', help='Automatically sanitized HTML contents'),
        'contrat_model': fields.selection([
            ('contrat_PP', 'Vendeur Pers et Acquéreur Pers'),
            ('contrat_PC', 'Vendeur Pers et Acquéreur Sté'),
            ('contrat_CP', 'Vendeur Sté et Acquéreur Pers'),
            ('contrat_CC', 'Vendeur Sté et Acquéreur Sté'),
            ], 'Modèle de Contrat'),
    }
    
    _defaults = {
                 'responsable_enrg': lambda s, cr, uid, c: uid,
                 'responsable_cf': lambda s, cr, uid, c: uid,
                 'responsable_quitus': lambda s, cr, uid, c: uid,
                 }


    # Form filling

sale_order()

class sale_order_line(osv.osv):
    _name = "sale.order.line"
    _inherit = "sale.order.line"
    _description = "Sales Order Line"
 
    def _calc_price_unit(self, cr, uid, line, context=None):
        val = 0.0
        line_obj = self.pool['sale.order.line']
        price = line_obj._calc_line_base_price(cr, uid, line, context=context)
        qty = line_obj._calc_line_quantity(cr, uid, line, context=context)
        if line.percentage_id:
            for c in self.pool['account.tax'].compute_all(cr, uid, line.percentage_id, price, qty,
                                        line.product_id,
                                        line.order_id.partner_id)['taxes']:
                val += c.get('amount', 0.0)
        else :
            val=price
        
        return val

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = self._calc_price_unit(cr, uid, line, context=context)
            qty = self._calc_line_quantity(cr, uid, line, context=context)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, qty,
                                        line.product_id,
                                        line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res

    
    _columns = {
        'tax_id': fields.many2many('account.tax', 'sale_order_tax', 'order_line_id', 'tax_id', 'Taxes', readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product UoS'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uos_qty': fields.float('Quantity (UoS)' , digits_compute=dp.get_precision('Product UoS'), readonly=True, states={'draft': [('readonly', False)]}),
        'product_uos': fields.many2one('product.uom', 'Product UoS'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)]}),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute=dp.get_precision('Account')),
        'percentage_id': fields.many2many('account.tax', 'sale_order_percentage', 'order_line_id', 'percentage_id', 'Pourcentage', readonly=True, states={'draft': [('readonly', False)]})
    }


    # Form filling

sale_order_line()


class notaire_dossier_transaction(osv.osv):
    _name = "notaire.dossier.transaction"
    _description = "Transactions related to a Folder"
    
    def _get_text_Recettes(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for sal in self.browse(cr, uid, ids, context=context):
                amount = sal.CFonds_Recettes
                text_amount = convertion.trad(amount, 'Dirham')
                res[sal.id] = text_amount.upper()              
        return res
    
    def _get_text_Depenses(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for sal in self.browse(cr, uid, ids, context=context):
                amount = sal.CFonds_Depenses
                text_amount = convertion.trad(amount, 'Dirham')
                res[sal.id] = text_amount.upper()              
        return res
    
    def print_receipt(self, cr, uid, ids, context=None):
        '''
        This function prints the receipt order and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
 #        self.signal_workflow(cr, uid, ids, 'quotation_sent')
 
        for line in self.browse(cr, uid,ids, context=context):
            if line.CFonds_Recettes :
                return self.pool['report'].get_action(cr, uid, ids, 'notaire.report_receiptorder', context=context)
            elif line.CFonds_Depenses :
                return self.pool['report'].get_action(cr, uid, ids, 'notaire.report_dechargeorder', context=context)

    _columns = {
        'name': fields.char('Libellé'),
        'transaction_id': fields.many2one('sale.order', 'Transaction of a folder', select=True),
        'date_transaction': fields.date('Date Transaction', select=True, copy=False),
        'Num_Cheque': fields.char('Numero de Chèque'),
        'Bank': fields.selection([
            ('WB2F', 'WB2/F'),
            ('CDGE', 'CDG/E'),
            ], 'Banque', copy=False, select=True),
        'CFrais_Recettes': fields.float('Compte des Frais Recette', required=True),
        'CFrais_Depenses': fields.float('Compte des Frais Depense', required=True),
        'CFonds_Recettes': fields.float('Compte des Fonds Recette', required=True),
        'CFonds_Recettes_text': fields.function(_get_text_Recettes, method=True, type='text', string='CFonds Recettes text', store=True),
        'CFonds_Depenses': fields.float('Compte des Fonds Depense', required=True),
        'CFonds_Depenses_text': fields.function(_get_text_Depenses, method=True, type='text', string='CFonds Depenses text', store=True),
    }


    # Form filling

notaire_dossier_transaction()

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'percentages_id': fields.many2many('account.tax', 'product_percentages_rel',
            'prod_id', 'percentage_id', 'Pourcentage',
            domain=[('parent_id','=',False),('type_tax_use','in',['sale','all'])]),

    }



# TODO add a field price_unit_uos
# - update it on change product and unit price
# - use it in report if there is a uos


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
