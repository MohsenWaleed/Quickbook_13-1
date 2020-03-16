# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from openerp import api, fields, models, _
from openerp.exceptions import UserError, AccessError
import csv
import base64
import io as StringIO
import xlrd
from openerp.tools import ustr
import requests
import codecs

class import_product_img_wizard(models.TransientModel):
    _name="import.product.img.wizard"

    import_type = fields.Selection([
        ('csv','CSV File'),
        ('excel','Excel File')
        ], default="csv", string="Import File Type", required=True)
    file = fields.Binary(string="File",required=True)
    product_by = fields.Selection([
        ('name','Name'),
        ('int_ref','Internal Reference'),
        ('barcode','Barcode')
        ], default="name", string = "Product By", required = True) 
    product_model = fields.Selection([
        ('pro_var','Product Variants'),
        ('pro_tmpl','Product Template')        
        ], default = "pro_var", string="Product Model", required = True)    
    
    @api.multi
    def show_success_msg(self,counter,skipped_line_no):
        
        #to close the current active wizard        
        action = self.env.ref('sh_all_in_one_import.sh_import_product_img_action').read()[0]
        action = {'type': 'ir.actions.act_window_close'} 
        
        #open the new success message box    
        view = self.env.ref('sh_message.sh_message_wizard')
        view_id = view and view.id or False                                   
        context = dict(self._context or {})
        dic_msg = str(counter) + " Records imported successfully"
        if skipped_line_no:
            dic_msg = dic_msg + "\nNote:"
        for k,v in skipped_line_no.items():
            dic_msg = dic_msg + "\nRow No " + k + " " + v + " "
        context['message'] = dic_msg   
        return {
            'name': 'Success',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.message.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
            }   

    
    @api.multi
    def import_product_img_apply(self):

        product_tmpl_obj = self.env['product.template']
        product_var_obj = self.env["product.product"]
        #perform import lead
        if self and self.file:
            #For CSV
            if self.import_type == 'csv':
                counter = 1
                skipped_line_no = {}
                try:
                    file = str(base64.decodestring(self.file).decode('utf-8'))
                    myreader = csv.reader(file.splitlines())
                    skip_header=True
                    
                    for row in myreader:
                        try:
                            if skip_header:
                                skip_header=False
                                counter = counter + 1
                                continue
                            
                            if row[0] not in (None,"") and row[1].strip() not in (None,""):
                                vals={}   
                                image_path = row[1].strip()
                                if "http://" in image_path or "https://" in image_path:
                                    try:
                                        r = requests.get(image_path)
                                        if r and r.content:
                                            image_base64 = base64.encodestring(r.content) 
                                            vals.update({'image': image_base64})
                                        else:
                                            skipped_line_no[str(counter)] = " - URL not correct or check your image size. "                                            
                                            counter = counter + 1                                                
                                            continue
                                    except Exception as e:
                                        skipped_line_no[str(counter)] = " - URL not correct or check your image size " + ustr(e)   
                                        counter = counter + 1 
                                        continue                                              
                                    
                                else:
                                    try:
                                        with open(image_path, 'rb') as image:
                                            image.seek(0)
                                            binary_data = image.read()
                                            image_base64 = codecs.encode(binary_data, 'base64')     
                                            if image_base64:
                                                vals.update({'image': image_base64})
                                            else:
                                                skipped_line_no[str(counter)] = " - Could not find the image or please make sure it is accessible to this app. "                                            
                                                counter = counter + 1                                                
                                                continue                                                                       
                                    except Exception as e:
                                        skipped_line_no[str(counter)] = " - Could not find the image or please make sure it is accessible to this app. " + ustr(e)   
                                        counter = counter + 1 
                                        continue  
                                

                                field_nm = 'name'
                                if self.product_by == 'name':
                                    field_nm = 'name'
                                elif self.product_by == 'int_ref':
                                    field_nm = 'default_code'
                                elif self.product_by == 'barcode':
                                    field_nm = 'barcode'

                                product_obj = False
                                if self.product_model == 'pro_var':
                                    product_obj = self.env["product.product"]
                                else:
                                    product_obj = self.env["product.template"]                                                                      
                                
                                search_product = product_obj.search([(field_nm,'=',row[0] )], limit = 1)                             
                                if search_product:
                                    search_product.write(vals)
                                    counter = counter + 1
                                else:
                                    skipped_line_no[str(counter)] = " - Product not found. "   
                                    counter = counter + 1 
                            else:
                                skipped_line_no[str(counter)] = " - Product or URL/Path field is empty. "   
                                counter = counter + 1 
                                continue                                                                     

                        except Exception as e:
                            skipped_line_no[str(counter)]=" - Value is not valid. " + ustr(e)   
                            counter = counter + 1 
                            continue          
                            
                except Exception:
                    raise UserError(_("Sorry, Your csv file does not match with our format"))
                
                if counter > 1:
                    completed_records = (counter - len(skipped_line_no)) - 2
                    res = self.show_success_msg(completed_records, skipped_line_no)
                    return res

            
            #For Excel
            if self.import_type == 'excel':
                counter = 1
                skipped_line_no = {}                  
                try:
                    wb = xlrd.open_workbook(file_contents=base64.decodestring(self.file))
                    sheet = wb.sheet_by_index(0)     
                    skip_header = True    
                    for row in range(sheet.nrows):
                        try:
                            if skip_header:
                                skip_header = False
                                counter = counter + 1
                                continue
                            
                            if sheet.cell(row,0).value not in (None,"") and sheet.cell(row,1).value.strip() not in (None,""):
                                vals={}   
                                image_path = sheet.cell(row,1).value.strip()
                                if "http://" in image_path or "https://" in image_path:
                                    try:
                                        r = requests.get(image_path)
                                        if r and r.content:
                                            image_base64 = base64.encodestring(r.content) 
                                            vals.update({'image': image_base64})
                                        else:
                                            skipped_line_no[str(counter)] = " - URL not correct or check your image size. "                                            
                                            counter = counter + 1                                                
                                            continue
                                    except Exception as e:
                                        skipped_line_no[str(counter)] = " - URL not correct or check your image size " + ustr(e)   
                                        counter = counter + 1 
                                        continue                                              
                                    
                                else:
                                    try:
                                        with open(image_path, 'rb') as image:
                                            image.seek(0)
                                            binary_data = image.read()
                                            image_base64 = codecs.encode(binary_data, 'base64')     
                                            if image_base64:
                                                vals.update({'image': image_base64})
                                            else:
                                                skipped_line_no[str(counter)] = " - Could not find the image or please make sure it is accessible to this app. "                                            
                                                counter = counter + 1                                                
                                                continue                                                                       
                                    except Exception as e:
                                        skipped_line_no[str(counter)] = " - Could not find the image or please make sure it is accessible to this app. " + ustr(e)   
                                        counter = counter + 1 
                                        continue  
                                

                                field_nm = 'name'
                                if self.product_by == 'name':
                                    field_nm = 'name'
                                elif self.product_by == 'int_ref':
                                    field_nm = 'default_code'
                                elif self.product_by == 'barcode':
                                    field_nm = 'barcode'

                                product_obj = False
                                if self.product_model == 'pro_var':
                                    product_obj = self.env["product.product"]
                                else:
                                    product_obj = self.env["product.template"]                                                                      
                                
                                search_product = product_obj.search([(field_nm,'=',sheet.cell(row,0).value )], limit = 1)                             
                                if search_product:
                                    search_product.write(vals)
                                    counter = counter + 1
                                else:
                                    skipped_line_no[str(counter)] = " - Product not found. "   
                                    counter = counter + 1 
                            else:
                                skipped_line_no[str(counter)] = " - Product or URL/Path field is empty. "   
                                counter = counter + 1 
                                continue                                                                     

                        except Exception as e:
                            skipped_line_no[str(counter)]=" - Value is not valid. " + ustr(e)   
                            counter = counter + 1 
                            continue          
                            
                except Exception:
                    raise UserError(_("Sorry, Your excel file does not match with our format"))
                
                if counter > 1:
                    completed_records = (counter - len(skipped_line_no)) - 2
                    res = self.show_success_msg(completed_records, skipped_line_no)
                    return res