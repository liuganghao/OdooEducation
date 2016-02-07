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

{
    'name': 'Notaire',
    'version': '1.0',
    'category': 'Gestion, Notary ',
    'description': """
This module aims to facilitate the work of a solicitor (notary).  
=================================================================

Use notes to write meeting minutes, organize ideas, organize personal todo
lists, etc. Each user manages his own personal Notes. Notes are available to
their authors only, but they can share notes to others users so that several
people can work on the same note in real time. It's very efficient to share
meeting minutes.

Notes can be found in the 'Home' menu.
""",
    'author': 'Ghandi',
    'website': 'None',
    'summary': 'Sticky notes, Collaborative, Memos',
    'sequence': 9,
    'depends': ['sale'],
    'data': ['account_invoice_view.xml',
             'notaire_view.xml',
             'res_partner_view.xml',
             'views/report_receiptorder.xml',
             'views/report_notaryquotation.xml',
             'views/report_fichecomptable.xml',
             'views/report_dechargeorder.xml',
             'views/report_contratnotaire.xml',
             'notaire_workflow.xml',
             'notaire_report.xml'],
    'demo': [],
    'test': [],
    'qweb': ['static/src/xml/base.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
