-- Seed organizations
INSERT INTO public.organizations (name, description, website, contact_email) VALUES
('Amnesty International', 'Global human rights organization working to protect people from injustice', 'https://amnesty.org', 'contact@amnesty.org'),
('Greenpeace', 'Environmental organization campaigning against climate change and ecological destruction', 'https://greenpeace.org', 'info@greenpeace.org'),
('Doctors Without Borders', 'Medical humanitarian organization providing emergency aid in conflict and disaster zones', 'https://msf.org', 'info@msf.org'),
('UNHCR', 'UN Refugee Agency protecting displaced people and stateless persons', 'https://unhcr.org', 'unhcr@unhcr.org'),
('Transparency International', 'Global movement against corruption and promoting transparency in government', 'https://transparency.org', 'ti@transparency.org'),
('Electronic Frontier Foundation', 'Nonprofit defending civil liberties in the digital world', 'https://eff.org', 'info@eff.org'),
('Human Rights Watch', 'Investigates and reports on human rights abuses worldwide', 'https://hrw.org', 'hrwnyc@hrw.org'),
('Oxfam', 'International confederation fighting poverty and injustice', 'https://oxfam.org', 'contact@oxfam.org'),
('WWF', 'Wildlife conservation organization focused on protecting endangered species and habitats', 'https://wwf.org', 'info@wwf.org'),
('Save the Children', 'Organization working to improve the lives of children through education and healthcare', 'https://savethechildren.org', 'info@savethechildren.org'),
('Wikipedia Foundation', 'Nonprofit supporting free knowledge and open access to information', 'https://wikimediafoundation.org', 'info@wikimedia.org'),
('Open Society Foundations', 'Grantmaking network supporting democracy, human rights, and social justice', 'https://opensocietyfoundations.org', 'info@opensocietyfoundations.org')
ON CONFLICT DO NOTHING;

-- Seed projects
INSERT INTO public.projects (name, description, organization_id) VALUES
('Climate Emergency Response', 'Campaigns and direct action against fossil fuel expansion and climate inaction', 2),
('Refugee Legal Aid', 'Providing legal assistance to asylum seekers and refugees', 4),
('Anti-Corruption Hotline', 'Reporting platform for corruption cases with legal follow-up', 5),
('Digital Rights Monitoring', 'Tracking government surveillance and protecting online privacy', 6),
('Child Education Access', 'Ensuring access to quality education for children in conflict zones', 10),
('Food Security Program', 'Combating hunger and food inequality in vulnerable communities', 8),
('Wildlife Protection Fund', 'Funding rangers and anti-poaching efforts globally', 9),
('Emergency Medical Response', 'Rapid deployment medical teams in disaster and war zones', 3),
('Human Rights Documentation', 'Documenting human rights violations for legal proceedings', 7),
('Freedom of Press Fund', 'Supporting journalists facing persecution for reporting truth', 1),
('Open Data Initiative', 'Promoting transparency through open government data', 11),
('Community Resilience Grants', 'Funding local grassroots organizations tackling social issues', 12)
ON CONFLICT DO NOTHING;

-- Seed solutions (reusable solution concepts)
INSERT INTO public.solutions (name, context, content) VALUES
('Donation to NGO', 'Financial support to organizations working on the problem', 'Direct monetary contribution to organizations solving this type of issue'),
('Petition Signing', 'Collective citizen pressure through signed petitions', 'Joining or creating petitions to pressure decision-makers'),
('Volunteering', 'Direct personal contribution of time and skills', 'Volunteering with organizations that address this type of problem'),
('Awareness Campaign', 'Spreading information to create public pressure', 'Sharing information and educating others about the issue'),
('Legal Action Support', 'Supporting legal efforts to address systemic problems', 'Funding or participating in legal challenges against injustice'),
('Policy Advocacy', 'Pushing for legislative and policy changes', 'Engaging with representatives and policy processes'),
('Community Organizing', 'Building local power to address shared problems', 'Joining or forming community groups to tackle local issues'),
('Boycott/Divestment', 'Economic pressure on bad actors', 'Withdrawing financial support from harmful entities'),
('Whistleblowing', 'Exposing wrongdoing through proper channels', 'Reporting misconduct to authorities or journalists'),
('Emergency Relief', 'Immediate humanitarian assistance', 'Providing or funding urgent help to those in crisis')
ON CONFLICT DO NOTHING;

-- Seed problems (common complaint categories)
INSERT INTO public.problems (name, context, content) VALUES
('Climate Change', 'Environmental degradation and global warming', 'Rising temperatures, extreme weather, fossil fuel dependency'),
('Political Corruption', 'Abuse of power and public trust', 'Bribery, nepotism, lack of government accountability'),
('Human Rights Violations', 'Abuse of fundamental human rights', 'Torture, unlawful detention, discrimination, censorship'),
('Refugee Crisis', 'Displacement of people due to conflict or persecution', 'Lack of safe passage, legal status issues, integration challenges'),
('Poverty and Inequality', 'Extreme economic disparities and lack of basic needs', 'Food insecurity, homelessness, lack of healthcare access'),
('Wildlife Extinction', 'Loss of biodiversity and species', 'Habitat destruction, poaching, illegal wildlife trade'),
('Digital Privacy', 'Surveillance and data exploitation', 'Government surveillance, data breaches, tech monopolies'),
('Freedom of Press', 'Restrictions on journalism and free speech', 'Censorship, journalist persecution, media monopolies'),
('Child Rights', 'Exploitation and neglect of children', 'Child labor, lack of education access, abuse'),
('Food Insecurity', 'Lack of access to nutritious food', 'Hunger, malnutrition, food waste, agricultural inequality')
ON CONFLICT DO NOTHING;
