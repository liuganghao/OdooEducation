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

from openerp.osv import fields,osv

class partner_nationality(osv.osv):
    _name = "partner.nationality"
    _description = "nationalite du partenaire"


    _columns = {       
        'name': fields.char('Nationalite'),                
    }

    # Form filling

partner_nationality()

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _sale_order_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,0), ids))
        # The current user may not have access rights for sale orders
        try:
            for partner in self.browse(cr, uid, ids, context):
                res[partner.id] = len(partner.sale_order_ids) + len(partner.mapped('child_ids.sale_order_ids'))
        except:
            pass
        return res

    _columns = {
        'sale_order_count': fields.function(_sale_order_count, string='# of Sales Order', type='integer'),
        'firstname_arabic' : fields.char(u'الإسم',size=100, required=True),
        'father_name': fields.char(u'nom de père'),
        'mother_name': fields.char(u'nom de mère'),
        'cin': fields.char('CIN', copy=False),
        'expiration_ci_date': fields.date('date d expiration CI', copy=False),
        'birth_place': fields.char('Lieu de naissance', copy=False),
        'birth_date': fields.date('date de naissance', copy=False),
        'seller': fields.boolean('Vendeur'),        
        'sale_order_ids': fields.one2many('sale.order','partner_id','Sales Order'),
        'nationality': fields.many2one('partner.nationality', 'Nationalite'),
        'marital_status': fields.selection([
            ('celibataire', 'Celibataire'),
            ('marie', 'Marie(e)'),
            ('veuf', 'Veuf(ve)'),
            ('divorce', 'Divorce(e)'),
            ], 'Etat Civil', copy=False, select=True),
        'loi_marital': fields.selection([
            ('islamique', 'Islamique'),
            ('autre', 'Autre Loi'),
            ], 'Loi de mariage', copy=False, select=True),
        'father_name_ar': fields.char('اسم الأب'),
        'mother_name_ar': fields.char('اسم الأم'),
        'street_ar': fields.char('العنوان'),
        'street2_ar': fields.char('2العنوان'),
        'city_ar': fields.char('المدينة'),
        'country_ar': fields.char('الدولة'),
        'nationality_ar': fields.selection([
            ('مغرب', 'مغرب'),
            ('أثيوبيا', 'أثيوبيا'),
            ('أذربيجان', 'أذربيجان'),
            ('أرمينيا', 'أرمينيا'),
            ('إسبانيا', 'إسبانيا'),
            ('إفريقيا الوسطى', 'إفريقيا الوسطى'),
            ('أفغانستان', 'أفغانستان'),
            ('ألبانيا', 'ألبانيا'),
            ('أمريكيا', 'أمريكيا'),
            ('إندونيسيا', 'إندونيسيا'),
            ], 'الجنسية', copy=False, select=True),
        'marital_status_ar': fields.selection([
            ('عازب(ة)', 'عازب(ة'),
            ('متزوج(ة)', 'متزوج(ة'),
            ('أرمل(ة)', 'أرمل(ة'),
            ('مطلق(ة)', 'مطلق(ة'),
            ], 'الحالة الاجتماعية', copy=False, select=True),
        'birth_place_ar': fields.char('مكان الإزدياد', copy=False),
        'job_ar': fields.char('العمل'),
        'tel': fields.char('الهاتف'),
        'tel_por': fields.char('الهاتق النقال'),
        'fax2': fields.char('فاكس'),
        'email_ar': fields.char('البريد الإلكتروني'),
        'civility_ar': fields.selection([
            ('السيد', 'السيد'),
            ('الدكتور', 'الدكتور'),
            ('الأستاد', 'الأستاد'),
            ], 'كياسة', copy=False, select=True),
        'price_sell': fields.float('Capital'),
        'Commerce_Tribunal': fields.char('Commerce de Tribunal de'),
        'Registre_Analytique_Num': fields.char('Numero de Registre Analysique'),
        'Identifiant_Fiscal': fields.char('Identifiant Fiscal'),
        
        
        
    }

    _sql_constraints = [
        ('cin_uniq', 'unique(cin)',
            'unique cin for each !'),
                        ]
