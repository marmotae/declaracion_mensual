# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from distutils.command.config import config
import frappe, erpnext, calendar, datetime
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr

myCompany = frappe.defaults.get_user_default("Company")
fiscalData = frappe.get_doc("ConfigFiscal",myCompany)
def get_columns():
	return [
		{
			"fieldname": "concepto",
			"label": _("Concepto"),
			"fieldtype": "Data",
			"options": "",
			"width": "300"
		},
		{
			"fieldname": "monto",
			"label": _("Monto"),
			"fieldtype": "Data",
			"options": "Currency",
			"width":"300"
		}
	]

def get_mes(mes):
	midic= {
		'Enero':1,
		'Febrero':2,
                'Marzo':3,
                'Abril':4,
                'Mayo':5,
                'Junio':6,
                'Julio':7,
                'Agosto':8,
                'Septiembre':9,
                'Octubre':10,
                'Noviembre':11,
                'Diciembre':12
	}
	return midic.get(mes)

def validate_filters(filters):
	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))
	if not filters.mes:
		frappe.throw(_("Mes is required"))
	fiscal_year = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True)
	if not fiscal_year:
		frappe.throw(_("Fiscal Year {0} does not exist").format(filters.fiscal_year))
	else:
		filters.year_start_date = getdate(fiscal_year.year_start_date)
		filters.year_end_date = getdate(fiscal_year.year_end_date)
	month = get_mes(filters.mes)
	strdate1 = filters.fiscal_year+"-"+str(month)+"-1"
	filters.from_date = getdate(strdate1)
	strdate2 = filters.fiscal_year+"-"+str(month)+"-"+str(calendar.monthrange(int(filters.fiscal_year), month)[1])
	filters.to_date = getdate(strdate2)

def agrega_record(record,data):
	for r in record:
		if r.monto is None:
			r.monto = 0
		if data is None:
			data = [r]
		else:
			data.append(r)
	return data

def get_ejercicio(tag,account,filters,data):
	fecha = filters.fiscal_year+"-01-01"
	record = frappe.db.sql("""select 
	%s as 'concepto', 
	round(abs(sum(debit)-sum(credit))) as 'monto' 
	from `tabGL Entry` where 
	account like %s 
	and posting_date <= %s 	
	""", [tag,account,filters.to_date.strftime("%Y-%m-%d")], as_dict=True)
	return agrega_record(record,data)

def get_periodos_anteriores(tag,account,filters,data):
	fecha = filters.fiscal_year+"-01-01"
	record = frappe.db.sql("""select 
	%s as 'concepto', 
	round(abs(sum(debit)-sum(credit))) as 'monto' 
	from `tabGL Entry` where 
	account like %s 
	and posting_date < %s and posting_date >= %s	
	""", [tag,account,filters.from_date.strftime("%Y-%m-%d"),fecha], as_dict=True)
	return agrega_record(record,data)

def get_periodo(tag,account,filters,data):
	record = frappe.db.sql("""select 
	%s as 'concepto', 
	round(abs(sum(debit)-sum(credit))) as 'monto' 
	from `tabGL Entry` where 
	account like %s 
	and posting_date >= %s and posting_date <= %s	
	""", [tag,account,filters.from_date.strftime("%Y-%m-%d"),filters.to_date.strftime("%Y-%m-%d")], as_dict=True)
	return agrega_record(record,data)

def get_ingresos_excentos(filters,data):
	return genera_cero("Ingresos Excentos",data)

def genera_valor(tag,monto,data):
	resultado = frappe._dict({
		"concepto":tag,
		"monto":monto
	})
	data.append(resultado)
	return data

def genera_cero(tag,data):
	return genera_valor(tag,0,data)

def get_total_de_ingresos_acumulables(filters,data):
	total_de_ingresos = data[1].get("monto")
	ingresos_excentos = data[2].get("monto")
	total_de_ingresos_acumulables = frappe._dict({
		"concepto":"Total de ingresos acumulables",
		"monto":total_de_ingresos-ingresos_excentos
	})
	data.append(total_de_ingresos_acumulables)
	return data

def getLastValue(data):
	return data[len(data)-1].monto

def get_tabla(doc,mes):
	midic= {
		'Enero':doc.tabla_enero,
		'Febrero':doc.tabla_febrero,
		'Marzo':doc.tabla_marzo,
		'Abril':doc.tabla_abril,
		'Mayo':doc.tabla_mayo,
		'Junio':doc.tabla_junio,
		'Julio':doc.tabla_julio,
		'Agosto':doc.tabla_agosto,
		'Septiembre':doc.tabla_septiembre,
		'Octubre':doc.tabla_octubre,
		'Noviembre':doc.tabla_noviembre,
		'Diciembre':doc.tabla_diciembre
	}
	return midic.get(mes)

def calcula_isr(monto,filters):
	doc = frappe.get_doc("pagos_provisionales_isr",filters.fiscal_year)
	tabla = get_tabla(doc,filters.mes)
	contador = 0
	while((tabla[contador].limite_superior <= monto)):
		contador=contador+1
	if(monto==0):
		return 0
	else:
		limite_inferior = tabla[contador].limite_inferior
		porcentaje_sobre_excedente = tabla[contador].porcentaje_sobre_excedente
		cuota_fija = tabla[contador].cuota_fija
		return round(((monto-limite_inferior)*(porcentaje_sobre_excedente/100)+cuota_fija),0)
def get_account_number(name):
	return (frappe.get_doc("Account",name).account_number)
def get_data(filters):
	data = None
	# [0] Cargamos ingresos de periodos anteriores
	data = get_periodos_anteriores("Ingresos de Periodos Anteriores","4.1.2.%%",filters,data)
	ingresos_periodos_anteriores = getLastValue(data)
	data = get_periodo("Ingresos del Periodo","4.1.2.%%",filters,data)
	ingresos_del_periodo = getLastValue(data)
	total_de_ingresos = ingresos_periodos_anteriores+ingresos_del_periodo
	data = genera_valor("Total de ingresos",total_de_ingresos,data)
	data = get_ingresos_excentos(filters,data)
	ingresos_excentos = getLastValue(data)
	total_de_ingresos_acumulables = total_de_ingresos - ingresos_excentos
	data = genera_valor("Total de ingresos acumulables",total_de_ingresos_acumulables,data)
	#Compras y gastos del periodo
	data = get_periodo("Compras y gastos del periodo","5%%",filters,data)
	data = get_periodos_anteriores("Compras y gastos de periodos anteriores","5%%",filters,data)
	data = get_ejercicio("Total de compras y gastos","5%%",filters,data)
	total_de_compras_y_gastos = getLastValue(data)
	data = genera_cero("Deducción de inversiones de ejercicios anteriores",data)
	deduccion_de_inversiones = getLastValue(data)
	data = genera_cero("Participación de los trabajadores en las utilidades",data)
	ptu  = getLastValue(data)
	base_gravable = total_de_ingresos_acumulables-(total_de_compras_y_gastos+deduccion_de_inversiones+ptu)
	if(base_gravable<0):
		base_gravable=0
	data = genera_valor("Base gravable",base_gravable,data)
	isr_causado = calcula_isr(base_gravable,filters)
	data = genera_valor("ISR Causado",isr_causado,data)
	cta_retenciones = get_account_number(fiscalData.grupo_retenciones_isr_terceros)+"%%"
	data = get_periodos_anteriores("ISR retenido de periodos anteriores",cta_retenciones,filters,data)
	retenciones_anteriores = getLastValue(data)
	data = get_periodo("ISR retenido del periodo",cta_retenciones,filters,data)
	retenciones_periodo = getLastValue(data)
	retenciones_totales = retenciones_anteriores+retenciones_periodo
	data = genera_valor("Total ISR retenido",retenciones_totales,data)
	isr_a_cargo = isr_causado-retenciones_totales
	if(isr_a_cargo<0):
		isr_a_cargo=0
	data = genera_valor("ISR a cargo",isr_a_cargo,data)
	cta_iva_16 = "4.1.2.0001%%"
	data = get_periodo("Actividades gravadas a la tasa del 16%",cta_iva_16,filters,data)
	cta_iva_trasladado = get_account_number(fiscalData.iva_trasladado)+"%%"
	#IVA cobrado del periodo a la tasa del 16%
	data = get_ejercicio("IVA cobrado del periodo a la tasa del 16%",cta_iva_trasladado,filters,data)
	iva_trasladado = getLastValue(data)
	#IVA Acreditable del periodo
	cta_iva_acreditable = get_account_number(fiscalData.iva_acreditable)+"%%"
	data = get_ejercicio("IVA acreditable del periodo",cta_iva_acreditable,filters,data)
	iva_acreditable = getLastValue(data)
	#IVA retenido por terceros
	cta_iva_retenido_terceros = get_account_number(fiscalData.iva_retenido_terceros)+"%%"
	data = get_ejercicio("IVA retenido por terceros en el periodo",cta_iva_retenido_terceros,filters,data)
	iva_retenido = getLastValue(data)
	iva_a_cargo = iva_trasladado-(iva_acreditable+iva_retenido)
	if(iva_a_cargo<0):
		iva_a_cargo = 0
	data = genera_valor("IVA a cargo",iva_a_cargo,data)
	return data

def execute(filters=None):
	validate_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	return columns, data
